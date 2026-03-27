# Refactor Guide: v1 → v2 (Powertools Migration)

> **Purpose**: Step-by-step instructions for a Kiro/Copilot coding session  
> **Branch**: `docs/refactor-powertools-architecture`  
> **Target branch for code**: `refactor/powertools-migration`  
> **Date**: 2026-03-26

This document is the single source of truth for the refactor session.
Follow the steps in order. Each step is independently mergeable.

---

## Prerequisites / Context

- Full architecture description: `docs/wiki/Architecture-v2.md`
- Security & privacy design (unchanged): `docs/wiki/Security-Privacy-Design.md`
- Existing business logic to preserve: `runtime/owner/onboarding_logic.py`
- Existing shared library to preserve: `runtime/shared/src/shared/`
- Existing tests to preserve: `runtime/tests/shared/`

---

## Step 1 – Consolidate CDK Stacks

**Goal**: Replace 5 stacks with 3. No Lambda or business logic changes.

### 1a. Create `infra/stacks/database_stack.py`

Merge the following existing stacks into one:
- `infra/stacks/owner_stack.py` → `owner_table`
- `infra/stacks/session_stack.py` → `owner_session_table` + `visitor_session_table`
- `infra/stacks/tag_stack.py` → `tag_table`

All tables keep their existing configuration (PK, BillingMode, RemovalPolicy, TTL).
The new class is named `DatabaseStack` and exports all 4 tables as public attributes.

### 1b. Update `infra/stacks/ui_stack.py`

Replace the current public S3 bucket with:
- S3 Bucket: `block_public_access=BlockPublicAccess.BLOCK_ALL`, `removal_policy=RemovalPolicy.RETAIN`
- CloudFront Distribution with Origin Access Control (OAC) pointed at the S3 bucket
- `default_root_object="index.html"`
- Error response: HTTP 404 → `/index.html` (required for Astro SPA routing)
- `CfnOutput` for both the bucket name and the CloudFront domain name

### 1c. Update `infra/stacks/api_stack.py`

- Change constructor to accept a `DatabaseStack` instance instead of `ApiStackResources`
- Add `RestApi` construct:
  - `rest_api_name=f"lost-and-found-{stage}"`
  - CORS preflight options (allow all origins for now, tighten in prod)
  - `StageOptions` with `MethodLoggingLevel.INFO`
- Add helper method `_add_proxy(root, prefix, fn)` that creates `/{prefix}` and `/{prefix}/{proxy+}` with `ANY` method → `LambdaIntegration`
- Wire: `/v1/owner`, `/v1/visitor`, `/v1/tag` (visitor Lambda does not exist yet, create placeholder)
- Add `CfnOutput` for the API URL

### 1d. Update `infra/stacks/__init__.py`

Export `DatabaseStack`, `ApiStack`, `UIStack`. Remove exports for old stacks.

### 1e. Update `infra/app.py`

```python
db = DatabaseStack(app, f"LostAndFoundDatabaseStack-{stage}", env=env, stage=stage)
api = ApiStack(app, f"LostAndFoundApiStack-{stage}", env=env, db_stack=db, stage=stage)
ui = UIStack(app, f"LostAndFoundUIStack-{stage}", env=env, stage=stage)
```

### 1f. Delete old stack files

- `infra/stacks/owner_stack.py`
- `infra/stacks/session_stack.py`
- `infra/stacks/tag_stack.py`

### 1g. Add CDK Assertion tests

Create `infra/tests/test_stacks.py` with tests for:
- `ResourceCountIs("AWS::ApiGateway::RestApi", 1)`
- `ResourceCountIs("AWS::Lambda::Function", 3)` (owner, visitor, tag)
- All 4 DynamoDB tables exist
- Session tables have `TimeToLiveSpecification` enabled (privacy requirement)
- S3 bucket has `BlockPublicAcls: true`
- CloudFront distribution exists

**Validation**: `cdk synth` must succeed. All CDK tests must pass.

---

## Step 2 – Introduce Powertools: Owner Lambda (Pilot)

**Goal**: Migrate the owner Lambda to Powertools routing. Preserve all business logic.

### 2a. Add Powertools to shared layer dependencies

In `runtime/shared/pyproject.toml`:

```toml
[tool.poetry.dependencies]
python = "^3.12"
pydantic = "^2.2.1"
requests = "^2.31.0"
aws-lambda-powertools = {version = "^3.0", extras = ["validation"]}
cryptography = "^44.0"
srptools = "^1.0"
mnemonic = "^0.21"
```

### 2b. Create `runtime/owner/app.py`

```python
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from routes.onboarding import router as onboarding_router
from routes.auth import router as auth_router
from routes.account import router as account_router
from routes.storage import router as storage_router

app = APIGatewayRestResolver(enable_validation=True)
app.include_router(onboarding_router, prefix="/v1/owner")
app.include_router(auth_router, prefix="/v1/owner")
app.include_router(account_router, prefix="/v1/owner")
app.include_router(storage_router, prefix="/v1/owner")
```

### 2c. Create `runtime/owner/lambda_handler.py`

```python
from aws_lambda_powertools.utilities.typing import LambdaContext
from app import app

def handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
```

### 2d. Create `runtime/owner/routes/onboarding.py`

Migrate from `Owner_handler_impl.py` `owner_onboarding` method.
- Import `onboarding_logic` from `onboarding_logic.py` (file stays, do not delete)
- Adjust call signature: pass validated Pydantic model instead of raw event dict
- `onboarding_logic.py` should be updated to accept `OnboardingRequest` directly
  and return `OnboardingInitResponse` instead of a raw dict

### 2e. Create `runtime/owner/routes/auth.py`

Stub routes for:
- `POST /login` → `owner_login` (returns 501 Not Implemented for now)
- `POST /logout` → `owner_logout` (returns 501)
- `POST /refresh` → `owner_session_refresh` (returns 501)

### 2f. Create `runtime/owner/routes/account.py`

Stub routes for:
- `GET /` → `owner_get` (migrate existing static response)
- `DELETE /` → `owner_delete_account` (returns 501)

### 2g. Create `runtime/owner/routes/storage.py`

Stub routes for:
- `GET /storage` → `owner_storage_get` (returns 501)
- `POST /storage` → `owner_storage` (returns 501)
- `DELETE /storage` → `owner_storage_delete` (returns 501)

### 2h. Delete old codegen files

- `runtime/owner/Owner_ABC.py`
- `runtime/owner/Owner_lambda_handler.py`
- `runtime/owner/Owner_handler_impl.py`

  ⚠️ Before deleting: verify all USER CODE blocks have been migrated.
  The only implemented block is `owner_onboarding` (→ `routes/onboarding.py`).
  All other blocks are `DEFAULT USER CODE: TODO` stubs – safe to discard.

### 2i. Add unit tests for owner routes

Create `runtime/tests/unit/owner/test_onboarding.py`:

```python
from moto import mock_aws
from owner.app import app

@mock_aws
def test_onboard_new_owner_returns_201():
    event = {
        "httpMethod": "POST",
        "path": "/v1/owner/onboarding",
        "body": '{"owner_hash": "owner_abc123abcabc123abcabc123abcabc123abcabc1234"}',
        "headers": {"Content-Type": "application/json"},
        "queryStringParameters": None,
        "requestContext": {"resourcePath": "/v1/owner/onboarding"}
    }
    result = app.resolve(event, {})
    assert result["statusCode"] == 201

@mock_aws
def test_onboard_duplicate_returns_409():
    # call twice with same owner_hash
    ...
```

**Validation**: `pytest runtime/tests/unit/owner/` must pass. `cdk synth` must still pass.

---

## Step 3 – Create Visitor Lambda (New)

**Goal**: Create the visitor Lambda from scratch following the same pattern.

> **Note**: The role is named `visitor` (not `finder`) to avoid trademark proximity
> to "FindR – The QR Code Network" and to better reflect the actual use case:
> anyone scanning a tag is a visitor, not necessarily a finder.

- Create `runtime/visitor/app.py`, `lambda_handler.py`
- Create `runtime/visitor/routes/session.py` – `POST /v1/visitor/session` (stub, 501)
- Create `runtime/visitor/routes/message.py` – `POST /v1/visitor/message` (stub, 501)
- Add unit tests: `runtime/tests/unit/visitor/`
- DynamoDB table: `visitor_session_table` (rename from `finder_session_table` if present)

---

## Step 4 – Migrate Tag Lambda

**Goal**: Apply Powertools pattern to tag Lambda. Check for existing implementation.

- Inspect existing `runtime/tag/` for any implemented logic (preserve it)
- Create `runtime/tag/app.py`, `lambda_handler.py`
- Create `runtime/tag/routes/tag_crud.py` – `GET /v1/tag/{tag_id}`
- Create `runtime/tag/routes/tag_status.py` – `PUT /v1/tag/{tag_id}/status`
- Add unit tests: `runtime/tests/unit/tag/`

---

## Step 5 – OpenAPI Export Tool

**Goal**: Replace `api/devtools/` with a single clean export script.

- Create `devtools/export_openapi.py`
- Import `app` from `owner`, `visitor`, `tag`
- Merge OpenAPI schemas from all three apps
- Write to `api/openapi.yaml` and `api/openapi.json`
- Add contract test: `runtime/tests/contract/test_openapi_contract.py`
- Delete `api/devtools/` and `api/schemas/` directories

---

## Step 6 – CI/CD Workflows

**Goal**: Replace existing workflows with the v2 CI/CD pipeline.

### Delete
- `.github/workflows/pylint.yml`

### Create/Replace
- `.github/workflows/ci.yml` – ruff, mypy (zoned), unit tests, contract tests, cdk synth
- `.github/workflows/deploy-dev.yml` – OIDC, build layer, export openapi, cdk deploy dev, integration tests
- `.github/workflows/deploy-prod.yml` – manual trigger, OIDC, cdk deploy prod
- `.github/workflows/security.yml` – bandit, checkov, trufflehog, pip-audit

### Update `pyproject.toml`

```toml
[tool.ruff]
select = ["E", "F", "I", "N", "UP"]

[tool.mypy]
python_version = "3.12"
strict = true

[[tool.mypy.overrides]]
module = ["aws_lambda_powertools.*", "boto3.*", "botocore.*", "moto.*"]
ignore_missing_imports = true
disallow_untyped_defs = false
```

### CDK Assertion tests – visitor check

In `infra/tests/test_stacks.py`, ensure:
- Lambda function for `visitor` exists (not `finder`)
- Route `/v1/visitor/{proxy+}` is wired
- `visitor_session_table` has TTL enabled

---

## Step 7 – Cleanup

- Delete `api/devtools/` if not done in Step 5
- Delete `api/schemas/` if not done in Step 5
- Review `docs/wiki/Notes to refine/` – promote or delete
- Update `docs/wiki/Architecture.md` to point to `Architecture-v2.md`
- Update `docs/wiki/ADR-Index.md` (see separate file)
- Verify: no remaining occurrences of `finder` (except in git history)
  - `grep -r "finder" runtime/ infra/ api/ --include="*.py" --include="*.yaml"`

---

## Invariants (must not change)

These must remain true after every step:

1. `cdk synth` succeeds
2. `pytest runtime/tests/shared/` passes (existing shared tests)
3. `owner_hash`, `session_token`, `tag_id` formats are unchanged
4. All DynamoDB table names are unchanged (no data migration needed) –
   **exception**: `finder_session_table` → `visitor_session_table` (v2 rename, no existing data)
5. Privacy: session tables always have TTL attribute set
6. No Cognito, no static AWS keys, no real email addresses in any model
7. All code, docs, and commits in English
8. Conventional Commits format
9. No occurrences of `finder`/`Finder` in runtime code, infra, or API routes
