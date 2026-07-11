# Applicant file format (.md)

One file = one loan applicant. The console reads it, runs the Trust Intelligence Engine, and
returns a verdict (Approve / Human Review / Reject). Sections are matched by keyword in the
`##` heading (case-insensitive), so wording can vary slightly.

## Sections

**## Applicant** — `- key: value` lines
| key | values |
|---|---|
| name | free text |
| employment | Freelancer / Salaried / Gig worker / Self-employed |
| occupation | free text |
| credit_history | `thin` / `established` / `none` |
| ekyc_verified | true / false |
| bureau_tradelines | integer (0 = no bureau record) |
| declared_monthly_income | number (VND) |

Optional (default to neutral if omitted; power the extra fraud + affordability checks):
| key | meaning |
|---|---|
| account_age_months | age of the bank account; under 3 = new-account caution (#3) |
| prior_applications | recent loan applications by this borrower; >2 = velocity flag (#3) |
| existing_monthly_debt | current monthly debt obligations, VND; used by the DSR test (#4) |
| payslip_monthly_income | employer pay-slip income (approved payroll partner) — corroboration (#8) |
| registry_monthly_income | national data centre / social-insurance registry income — corroboration (#8) |

Corroboration sources (`payslip_monthly_income`, `registry_monthly_income`) never change the Trust
Score. When they AGREE with observed Open-Banking inflow they lift *confidence*; a material
conflict is raised to the fraud layer. Omit them and nothing is penalised — missing is not bad.

**## Loan Request** — `- key: value`
`requested_amount`, `tenor_months`, `purpose`.

**## Monthly Inflow (Open Banking)** — one line per month, most recent 6 months:
`- 2026-01: 18200000`  (label before the colon is free; the number is what matters)

**## Monthly Outflow (per month)** — recurring monthly spend, pipe-separated:
`- <category> | <type> | <amount> | <on_time>`
- category: rent, food, transport, utility, insurance, shopping, other
- type: `expense` or `payment` (recurring bills like utility/insurance use `payment`)
- on_time: `on_time` / `yes` / `true`  ·  or  `missed` / `no` / `false`

Numbers may include commas or spaces; `VND` is ignored. See `aom.md`, `bao.md`, `chi.md`, `dat.md`.
