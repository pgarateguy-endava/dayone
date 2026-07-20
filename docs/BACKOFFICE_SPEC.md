# Backoffice - local MVP requirements

## Goal

Create an internal local web interface to start and operate a technical onboarding without running
scattered manual steps. The UI is an operator surface over the Bench catalog and state; it simulates
permissions and does not provision production access.

## Primary user

- Manager.
- Tech lead.
- Engineering enablement.
- People/IT admin.

## Current local MVP form

Required fields:

- `employee_name`
- `employee_email`
- `profile_id`
- `track_id`

Optional fields:

- `start_date`
- `buddy_email` (deferred until the onboarding domain has a buddy record)
- `seniority` (deferred)
- `location` (deferred)
- `notes` (deferred)

The current local UI also accepts an optional bench start date and employee profile PDF because the
date drives lifecycle notifications and the PDF supplies deterministic study suggestions.

## "Create onboarding" button actions

1. Validate profile.
2. Validate track.
3. Generate plan.
4. Create state record.
5. Calculate expected permissions from the selected role/profile; never from generated text.
6. Create day 1 tasks.
7. Flag required approvals.
8. Redirect the operator to the employee detail view. Teams/proactive delivery is simulated through
   the local notification queue; a real employee link is deferred.

## Detail view

Must show:

- Generated plan.
- Repositories.
- Requested permissions.
- Approved permissions.
- Checklist.
- Progress.
- Risks.
- Action logs.

For the local MVP, requested/approved permissions are simulated read-only state. The detail view may
show pending approval flags, but it must not grant access. Reports remain durable local files even if
the person is later archived.

## Catalog and lifecycle administration

The UI must expose these entities through discoverable navigation and provide create, edit, and
delete/archive behavior where stated:

| Entity | Required behavior | Safety rule |
|---|---|---|
| Roles/profiles | create, inline edit, delete | block deletion while assigned |
| Tracks | create, edit, delete | block deletion while assigned |
| Tasks | add, inline edit, delete | preserve existing employee history |
| Knowledge | create, inline edit, delete | preserve links and tags exactly |
| Responsibles | add, edit, remove | show report recipient effect |
| People | create, edit, archive/remove | preserve reports and audit history |

Progress updates, AM/PM check-ins, date changes, report generation, and notification delivery are
also audited mutations, not only catalog edits.

## Onboarding states

- `draft`
- `pending_approval`
- `ready_for_day_1`
- `in_progress`
- `blocked`
- `completed`

The local UI currently derives `inactive`, `pre_bench`, and `active` from the bench start date. The
full approval-oriented state machine remains a later onboarding capability; the UI must label this
boundary instead of presenting a simulated state as a real access decision.

## Security rules

- The backoffice must not grant sensitive production access without approval.
- Every action must be audited.
- The employee should only see authorized information.
- Permission templates must be versioned and reviewed by security/platform.
- The current localhost MVP is a trusted operator tool only. It must not be presented as a hosted
  employee-facing backoffice until authentication, authorization, and information filtering exist.

## Acceptance criteria for UI completion

- A user can discover every catalog view from the navigation and complete each CRUD flow without
  editing raw YAML or using an undocumented endpoint.
- A user can create, edit, review, and archive a person; protected role/track deletion returns a clear
  error; archived people retain reports and action history.
- A user can assign, edit, and remove a responsible and verify the recipient in the generated EOD
  report and local notification log.
- The end-to-end test suite covers the flows above plus changing the bench start date and observing
  immediate lifecycle notification evaluation.
- The UI shows simulated approval/pending information but never reports sensitive access as granted
  without an explicit approval state.
