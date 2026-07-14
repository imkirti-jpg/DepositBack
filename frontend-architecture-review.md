# DepositBack Frontend Architecture Review (Pre-Implementation)

## 1) Scope and Constraints

This architecture targets a single shared codebase for:
- Expo (iOS/Android)
- React Native Web
- TypeScript

Required libraries:
- Expo Router
- React Query
- NativeWind
- React Hook Form
- Zod
- Axios
- Supabase

Non-goals:
- No backend API changes
- No frontend implementation code in this document

---

## 2) Recommended Frontend Folder Structure

```text
frontend/
  app/
    _layout.tsx
    +not-found.tsx

    (public)/
      _layout.tsx
      welcome.tsx

    (auth)/
      _layout.tsx
      sign-in.tsx
      verify-otp.tsx

    (app)/
      _layout.tsx
      index.tsx                       # property list/home
      profile.tsx
      preferences.tsx

      properties/
        create.tsx
        [propertyId]/
          _layout.tsx
          dashboard.tsx
          edit.tsx

          lease/
            upload.tsx
            [leaseId].tsx            # lease status + extracted fields review

          evidence/
            index.tsx
            upload.tsx
            [evidenceId].tsx

          notice/
            create.tsx
            [noticeId].tsx            # notice status + claims list

          claims/
            [claimId].tsx             # override label

          documents/
            index.tsx
            create.tsx
            [docId].tsx               # polling + edit + mark sent

  src/
    api/
      client.ts                       # axios instance + auth header injection
      endpoints.ts                    # typed endpoint definitions
      errors.ts                       # API error mapping model

    auth/
      supabase.ts                     # Supabase client init
      session.ts                      # token/session helpers
      guards.ts                       # route guards for Expo Router
      auth-provider.tsx               # Auth context provider

    features/
      profile/
        api.ts
        schemas.ts
        hooks.ts
        ui/

      preferences/
        api.ts
        schemas.ts
        hooks.ts
        ui/

      properties/
        api.ts
        schemas.ts
        hooks.ts
        ui/

      lease/
        api.ts
        schemas.ts
        hooks.ts
        polling.ts
        ui/

      evidence/
        api.ts
        schemas.ts
        hooks.ts
        ui/

      disputes/
        api.ts
        schemas.ts
        hooks.ts
        polling.ts
        ui/

      documents/
        api.ts
        schemas.ts
        hooks.ts
        polling.ts
        ui/

      dashboard/
        api.ts
        schemas.ts
        hooks.ts
        ui/

    forms/
      fields/
      adapters/
      validators/

    components/
      ui/                             # Button, Input, Card, Modal, Badge, etc.
      feedback/                       # ErrorView, EmptyState, Skeletons
      layout/                         # Screen, Section, Header wrappers

    hooks/
      useDebouncedValue.ts
      useOnlineStatus.ts
      useAppForeground.ts

    lib/
      query-client.ts                 # React Query defaults
      query-keys.ts                   # cache key factory
      formatters.ts                   # currency/date/enum formatters
      constants.ts

    state/
      app-state.tsx                   # small global UI/session state with Context

    theme/
      tokens.ts                       # semantic tokens
      tailwind.config.ts              # NativeWind extension
      typography.ts

    types/
      api.ts
      domain.ts
      enums.ts

    config/
      env.ts
      runtime.ts

    testing/
      mocks/
      fixtures/
      contract/
```

Why this shape:
- Route-level separation in app/ for navigation clarity
- Feature modules for vertical ownership (api + hooks + ui + validation)
- Shared API client and query key conventions to avoid cache drift

---

## 3) Navigation Architecture (Expo Router)

Primary route groups:
- (public): onboarding/welcome
- (auth): sign in and OTP verification
- (app): all protected routes

Shell strategy:
- Root layout initializes providers: AuthProvider, QueryClientProvider, ThemeProvider
- Protected layout checks authenticated session and redirects to (auth) when absent

Per-property workflow subtree:
- properties/[propertyId]/dashboard is workflow anchor
- Child routes for lease, evidence, notice/claims, documents

Recommended navigation model:
- Stack for each property workflow
- Tabs only at global app level if needed (Home, Profile, Preferences)
- Keep workflow linear with visible progress state from dashboard.next_action

---

## 4) Authentication Flow (Supabase + FastAPI Bearer)

Backend expectation:
- Every protected endpoint requires Authorization: Bearer <supabase_access_token>
- Token audience must be authenticated
- Backend provisions user profile lazily on first valid request

Frontend flow:
1. User signs in via Supabase client (OTP or password, depending on product decision).
2. Supabase session is stored using secure platform storage.
3. Axios request interceptor injects access token into Authorization header.
4. On 401:
   - Attempt Supabase token refresh once.
   - Retry failed request once if refresh succeeds.
   - If refresh fails, clear session and redirect to (auth)/sign-in.
5. On app boot, hydrate session before mounting protected routes.

Session ownership boundaries:
- Supabase SDK is source of truth for auth state
- Backend /me is source of truth for profile row and server-side identity consistency

---

## 5) API Layer Design

## 5.1 Transport and typing

- Axios as HTTP transport
- Zod schemas at API boundary for parse-and-fail-fast
- DTO-to-domain mapping in feature api.ts files
- React Query handles async cache lifecycle

Request categories:
- JSON requests: profile/properties/preferences/claims/doc updates
- multipart/form-data uploads: lease, evidence, deduction notices

## 5.2 Endpoint contract matrix (all current backend endpoints)

Public/utility:
- GET /health
- GET /

Profile:
- GET /me -> ProfileResponse
- PUT /me -> ProfileResponse

Preferences:
- GET /preferences -> PreferencesResponse
- PUT /preferences -> PreferencesResponse

Properties:
- POST /properties -> PropertyResponse
- GET /properties -> PropertyResponse[]
- GET /properties/{property_id} -> PropertyResponse
- PUT /properties/{property_id} -> PropertyResponse

Lease:
- POST /lease (multipart: property_id, file) -> LeaseResponse (202, status=processing)
- GET /lease/{lease_id} -> LeaseResponse
- PUT /lease/{lease_id} -> LeaseResponse
- POST /lease/{lease_id}/reextract -> LeaseResponse (202)

Evidence:
- POST /evidence (multipart: property_id, phase, file, room_label?, notes?) -> EvidenceResponse
- GET /evidence?property_id=...&phase?=...&room_label?=... -> EvidenceResponse[]
- GET /evidence/{evidence_id} -> EvidenceResponse
- DELETE /evidence/{evidence_id} -> 204

Disputes:
- POST /deduction-notices (multipart: property_id, file?, raw_text?) -> NoticeResponse (202)
- GET /deduction-notices/{notice_id} -> NoticeResponse
- GET /deduction-notices/{notice_id}/claims -> ClaimResponse[]
- PUT /claims/{claim_id} -> ClaimResponse

Documents:
- POST /generated-documents -> DocumentResponse (202)
- GET /generated-documents/{doc_id} -> DocumentResponse
- PUT /generated-documents/{doc_id} -> DocumentResponse
- POST /generated-documents/{doc_id}/mark-sent -> DocumentResponse
- GET /generated-documents?property_id=... -> DocumentResponse[]

Dashboard:
- GET /properties/{property_id}/dashboard -> DashboardResponse

## 5.3 React Query ownership model

Query keys:
- me
- preferences
- properties.list
- properties.detail(propertyId)
- lease.detail(leaseId)
- evidence.list(propertyId, filters)
- evidence.detail(evidenceId)
- notice.detail(noticeId)
- notice.claims(noticeId)
- documents.list(propertyId)
- documents.detail(docId)
- dashboard(propertyId)

Mutations invalidate minimally:
- profile update -> me
- property update/create -> properties.list + properties.detail
- lease upload/reextract/update -> lease.detail + dashboard(propertyId)
- evidence upload/delete -> evidence.list + dashboard(propertyId)
- notice create -> notice.detail + notice.claims + dashboard(propertyId)
- claim override -> notice.claims + dashboard(propertyId)
- document create/update/mark-sent -> documents.detail + documents.list + dashboard(propertyId)

---

## 6) Reusable Component Architecture

Cross-platform primitives:
- Screen: safe area + scroll/layout normalization
- SectionCard: titled content group
- StatusBadge: enum-to-style mapping (processing, failed, draft, etc.)
- CurrencyText and DateText display helpers
- FormField wrappers for RHF + NativeWind styling
- UploadPicker and UploadPreview primitives (platform-specific adapters hidden)
- AsyncState components:
  - FullPageLoader
  - InlineSpinner
  - Skeleton blocks
  - EmptyState
  - ErrorState with retry action

Domain composites:
- LeaseStatusPanel
- ClaimListItem
- ClaimOverrideSheet
- DocumentEditorPanel
- NextActionBanner
- EvidenceFilterBar

---

## 7) Hooks Strategy

Feature hooks:
- useMeQuery, useUpdateMeMutation
- usePreferencesQuery, useUpdatePreferencesMutation
- usePropertiesQuery, useCreatePropertyMutation, useUpdatePropertyMutation
- useLeaseQuery, useUploadLeaseMutation, useUpdateLeaseMutation, useReextractLeaseMutation
- useEvidenceListQuery, useUploadEvidenceMutation, useDeleteEvidenceMutation
- useNoticeQuery, useCreateNoticeMutation, useNoticeClaimsQuery, useOverrideClaimMutation
- useDocumentsQuery, useDocumentQuery, useCreateDocumentMutation, useUpdateDocumentMutation, useMarkSentMutation
- useDashboardQuery

Polling hooks:
- useLeasePolling(leaseId)
- useNoticePolling(noticeId)
- useDocumentPolling(docId)

Form hooks:
- usePropertyForm
- useProfileForm
- usePreferenceForm
- useNoticeForm
- useDocumentEditForm

---

## 8) State Management Plan

Primary state source:
- Server state: React Query

Minimal client state:
- Auth/session metadata in Auth context
- UI-only transient state (modals, selected filters, current property id) in lightweight Context

Do not duplicate server data in local global stores.

Derived state strategy:
- Derive workflow step from dashboard payload:
  - lease_status
  - notice_status
  - documents[] status
  - next_action

---

## 9) Theme Structure (NativeWind)

Theme layers:
- Core tokens: spacing, radius, typography scale, shadow, z-index
- Semantic tokens: background, card, text-primary, text-muted, success, warning, danger, info, border
- Status colors by backend enum:
  - processing
  - needs_review
  - confirmed
  - failed
  - completed
  - draft
  - sent
  - supported/weak/unsupported/unclear

Typography guidance:
- Single cross-platform type ramp
- Readability-first line-height for document and claim reasoning views

Dark mode:
- Keep tokenized from day one even if launch is light-only

---

## 10) Error Handling Strategy

Three-tier classification:
1. Auth errors (401/403)
2. Validation/business errors (400/404/409/422)
3. Transport/system errors (timeouts, offline, 5xx)

Mapping rules:
- 400: show server detail directly where safe (upload type/size errors are useful)
- 404: show not-found screen and navigate to safe parent
- 409: conflict-specific CTA (e.g., "still processing, retry later")
- 422: form-level error mapping when field-level details exist
- 5xx/network: generic resilient message + retry

Observability:
- Add structured client logging for endpoint, status, correlation id (when available), and screen context
- Keep user messages human, logs technical

---

## 11) Loading Strategy

Global boot:
- App boot splash until auth session hydration completes

Screen loading levels:
- Initial page load: skeleton-first for dashboard, claims, documents list
- Background refetch: subtle inline spinner without layout shift
- Mutation pending: disable only affected controls, keep rest interactive

Upload/generation UX:
- Show pending cards immediately after 202 responses
- Bind UI status to polled resource status instead of optimistic "done"

---

## 12) Polling Strategy (Critical)

Resources requiring polling:
- Lease extraction: LeaseResponse.status (processing -> needs_review|confirmed|failed)
- Notice analysis: NoticeResponse.status (processing -> completed|failed)
- Document generation: DocumentResponse.status (processing -> draft|failed)

Policy:
- Start polling after create/reextract mutation success
- Poll interval:
  - foreground: 2-3 seconds
  - background/app inactive: pause polling
- Stop polling when status is terminal
- Hard timeout guard (for UX only): after N minutes, switch to "taking longer than expected" with manual retry

Cascade refresh on terminal transitions:
- Invalidate dashboard(propertyId)
- Invalidate dependent lists (claims/documents)

Failure handling:
- failed status shows explicit recovery CTA:
  - lease failed -> Re-extract
  - notice failed -> Re-submit notice
  - document failed -> Generate again

---

## 13) Response Models to Mirror in TypeScript

Core enums to model exactly from backend:
- PropertyStatus: active | resolved
- LeaseStatus: processing | needs_review | confirmed | failed
- EvidencePhase: move_in | move_out
- NoticeStatus: processing | completed | failed
- ClaimLabel: supported | weak | unsupported | unclear
- DocType: message | formal_letter
- DocStatus: processing | draft | sent | failed

Primary DTOs:
- ProfileResponse
- PreferencesResponse
- PropertyResponse
- LeaseResponse
- EvidenceResponse
- NoticeResponse
- ClaimResponse (effective_label included)
- DocumentResponse (display_content included)
- DashboardResponse (includes next_action)

---

## 14) Upload Workflow Architecture

Lease upload:
- multipart POST /lease
- Receive 202 + lease id/status=processing
- Route to lease detail and begin polling

Evidence upload:
- multipart POST /evidence
- Immediate 201; refresh list and dashboard counts

Deduction notice upload:
- multipart POST /deduction-notices
- At least one of file or raw_text required
- Receive 202 + notice id/status=processing
- Route to notice detail and poll until completed

File constraints currently inferred from backend storage service:
- Allowed MIME: image/jpeg, image/png, image/webp, image/heic, image/heif, application/pdf
- Max size: MAX_UPLOAD_SIZE_MB from backend env

---

## 15) Dashboard Flow Architecture

Dashboard is source of truth for workflow progression per property.

Expected dashboard-driven UI sections:
- Property summary and deposit amount
- Lease status and action
- Evidence counts by phase
- Notice status
- Claims summary totals:
  - total_supported_amount
  - total_disputed_amount
  - total_unquantified_count
- Generated document summaries
- next_action banner

Navigation decisions should prefer dashboard.next_action guidance for CTA priority.

---

## 16) Missing Documentation and Risks

Missing or unclear items discovered:
1. Auth method ambiguity:
   - There are two auth verification implementations in backend codebase style history (JWT secret based and JWKS based).
   - Active route dependency appears to use JWKS verification from Supabase.
2. API base path versioning:
   - Routers are in app/api/v1 but no /api/v1 prefix is mounted in main.py.
   - Need confirmation that production path is root-prefixed as currently coded.
3. Request/response examples are missing:
   - No canonical sample payloads for each endpoint.
4. Error contract is undocumented:
   - Need standardized error schema for all endpoints.
5. Pagination strategy not defined:
   - /properties, /evidence, /generated-documents, /claims currently appear unpaginated.
6. Time format and timezone guarantees not documented:
   - Assume ISO-8601 UTC, but should be explicit.
7. Upload UX metadata not documented:
   - No endpoint describes remaining size quota or expected processing SLA.
8. Polling guidance missing:
   - No recommended poll interval/backoff from backend side.
9. Lease extracted_fields schema is semi-structured:
   - Need stable contract for each field key and nested confidence/value shape.
10. Correlation/tracing ids:
   - No documented request id header for client logging and support debugging.
11. Supabase auth flow choice for frontend:
   - OTP vs password-first is not formalized.
12. Localization/currency formatting rules:
   - INR formatting implied in document generation prompts, but frontend display spec not defined.

---

## 17) Questions to Resolve Before Implementation

Authentication and session:
1. Should frontend launch with OTP-only auth, password auth, or both in UI?
2. Which Supabase session persistence policy is required for web vs native (remember me behavior)?

API contracts:
3. Can we get authoritative OpenAPI docs or frozen request/response examples for every endpoint?
4. Is the deployed API path root-based (for example /me) or prefixed (for example /api/v1/me)?
5. What is the canonical error JSON format for all 4xx/5xx responses?

Polling and async jobs:
6. What polling interval and timeout does backend team recommend for lease, notice, and document jobs?
7. Is there any server-side timeout after which processing rows should be considered stale?

Uploads:
8. What exact MAX_UPLOAD_SIZE_MB is configured per environment (dev/stage/prod)?
9. Should frontend compress/resize images before upload on mobile, and if yes, what target limits?

Data semantics:
10. Is LeaseResponse.extracted_fields contract frozen for v1, including low_confidence_fields keys?
11. Should ClaimResponse.reasoning be rendered as plain text only, or can it include markdown/newlines?
12. Should DocumentResponse.display_content be treated as plain text or rich text markdown?

Dashboard and workflow:
13. Is dashboard.next_action considered product-authoritative copy or can frontend adapt/rephrase per platform?
14. What is expected behavior when a property has multiple notices or multiple leases (always latest, or selectable history)?

Operational:
15. Is there a request-id header we should log client-side for support/debugging?
16. Are there rate limits we should surface proactively in UI messaging?

---

## 18) Architecture Review Summary

This architecture is viable for production-quality frontend delivery on Expo + React Native Web with the required libraries and no backend changes.

Most critical review gates before coding:
- Confirm auth path and session UX
- Freeze endpoint examples and error schema
- Confirm async polling SLAs and stale-processing policy
- Freeze extracted_fields and document content rendering assumptions

Once these are answered, implementation can proceed safely with low contract risk.
