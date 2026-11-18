# Tutorial: set up and use the intake forms

Primer Contacto's intake is two Google Forms that feed one Google Sheet. Teachers only fill in the forms; a script keeps the sheet up to date. Fields and rules are in [schema.md](schema.md).

| Piece | What it is | Who uses it |
|---|---|---|
| **Form A: New request** | One per request, under 2 minutes | Teacher |
| **Form B: Stage update** | One each time a request moves, under 30 seconds | Teacher |
| **Request Log sheet** | One row per request, in the wide CSV format the app reads | Nobody edits it by hand |

All pilot teachers share one set of forms and one sheet. Each teacher picks their name first; in Form B they only ever see their own requests. The sheet stores a code (`T1`, `T2`, …), never the name.

**Privacy:** the forms never ask for client names, Instagram handles, phone numbers, emails or street addresses. Requests are identified by an ID like `2026-11-14-A`.

---

## Part 1: Set up (once for the whole pilot, about 5 minutes)

1. Sign in to the Google account that will own the sheet, and go to **script.google.com** → **New project**.
2. Click **Untitled project** at the top left and rename it **Primer Contacto – Intake**.
3. Open `Code.gs`, delete everything in it, and paste in all of [`intake/setup_intake.gs`](../intake/setup_intake.gs).
4. Near the top of `Code.gs`, find `CONFIG.teachers` and replace `Teacher 1` … `Teacher 4` with the pilot teachers' names (keep the codes `T1` … `T4`). Do this only in Apps Script; never commit real names to GitHub.
5. Click the gear icon (**Project Settings**) and tick **Show "appsscript.json" manifest file in editor**. Back in the editor, open `appsscript.json` and replace its contents with [`intake/appsscript.json`](../intake/appsscript.json).
6. Click **Save**. Choose **setup** in the function menu at the top and click **Run**.
7. Approve the permissions: **Review permissions** → your account → **Advanced** → **Go to Primer Contacto – Intake (unsafe)** → **Allow**. "Unsafe" only means Google hasn't reviewed your own script.
8. Wait 30–60 seconds. The **Execution log** prints three links: the Request Log sheet, Form A and Form B.

You don't need **Deploy**. The script runs through two triggers that `setup` installs; you can see them under the clock icon (**Triggers**): `onNewRequest` and `onStageUpdate`.

Run `showLinks` any time to print the links again.

---

## Part 2: Daily use (teacher)

**When a request arrives, fill in Form A:**

| Question | What to enter |
|---|---|
| Who are you? | Your name |
| When did the request arrive? | The time it arrived, not the time you're logging it |
| Where did it come from? | Instagram DM, Linktree form, text, email, phone, in person, referral, other |
| Request type | Private session, small group, corporate, school event, community event, workshop, class series, other |
| Language | English, Spanish, both, other |
| Client type | Individual, company, school, nonprofit/community, studio, other |
| Event ZIP *(optional)* | 5-digit ZIP of the event, never a street address |
| Quoted amount *(optional)* | USD, if you already quoted |
| What did they ask for? *(optional)* | Short description. No names, handles or numbers |
| Have you replied? | **Yes, just now**, **Yes, earlier** (then enter when), or **Not yet**. A phone call you answered or an in-person conversation counts as replied when it arrived |

The sheet gets a new row with an ID such as `2026-11-14-A`, your teacher code and outcome **open**. If you've replied, replied_at is filled and last stage is **replied**; otherwise **received**.

**Each time the request moves, fill in Form B:**

| Question | What to enter |
|---|---|
| Who are you? | Your name. The form jumps to your own section |
| Request ID | Pick it from the list (only your open requests, newest first) |
| New stage | Replied, Quoted, Confirmed, Delivered, Invoiced, Paid, or Lost |
| When did it happen? | Date and time of that step |
| If lost: why? | No reply from client, declined price, scheduling conflict, went elsewhere, cancelled, other |
| Quoted amount *(optional)* | When the stage is Quoted |
| Note *(optional)* | No names |

The script fills in that stage's date. It never fills in skipped stages, so gaps stay visible for `validate.py`.

**When a request leaves the list:** once it's **Lost**, or **Delivered and Paid**, it disappears from Form B's list. Invoiced is only for contracted gigs (company, school, community organization).

**Tip:** open both form links on your phone and choose **Add to Home Screen**, so logging takes one tap.

---

## Part 3: Check that it works (about 10 minutes)

Keep the sheet's **Requests** tab open and refresh it after each step. Reload Form B before each update.

| # | Form | Enter | Check in the sheet |
|---|---|---|---|
| 1 | A | Teacher 1; today 10:00, Instagram DM, Private session, English, Individual; replied: **Not yet** | New row `<today>-A`, teacher_id **T1**, outcome **open**, last_stage **received**, replied_at blank |
| 2 | A | Teacher 2; today 11:00, Email, Corporate session, Both, Company, ZIP 60601; replied: **Yes, earlier**, today 11:20 | Row `<today>-B`, teacher_id **T2**, event_zip **60601**, replied_at **11:20**, last_stage **replied** |
| 2b | A | Teacher 3; today 09:00, Phone call, Private session, Español, Individual; replied: **Yes, just now** | replied_at **09:00** (the arrival time, not now) |
| 3 | B | Choose Teacher 1, click Next | Only `-A` is listed; Teacher 2's and 3's requests are not |
| 4 | B | Teacher 1: `-A` → Replied, today 10:30 | replied_at filled, last_stage **replied** |
| 5 | B | Teacher 1: `-A` → Quoted, today 11:00, amount 90 | quoted_at filled, quoted_amount **$90.00** |
| 6 | B | Teacher 1: `-A` → Confirmed, then Delivered, then Paid | outcome **delivered_paid**; Teacher 1's list shows "No open requests yet" |
| 7 | B | Teacher 2: `-B` → Lost, reason Declined price | lost_at filled, lost_reason **declined_price**, outcome **lost** |
| 8 | Phone | Open both forms | They load cleanly; one new request takes under 2 minutes |

If every check matches, the intake works.

**If something goes wrong**
- **No new row:** in the script editor open **Executions** (list icon on the left) and look for a red error.
- **Form B's list didn't change:** reload the form; Google caches it for a few seconds.
- **"Already set up" error:** `setup` refuses to run twice so nothing is duplicated. Run `resetSetup` first only if you really want new forms.

**Before giving the forms to the teachers:** delete the test rows, or run `resetSetup` then `setup` to create fresh forms and a clean sheet (the links change, so send the new ones).

---

## Part 4: Synthetic data (for building the app)

```bash
python generate_synthetic.py                    # 80 requests, 3-week pilot (Nov 16 – Dec 7, 2026)
python generate_synthetic.py --n 400 --weeks 52 --start 2025-11-17 --out data/synthetic_year.csv
python generate_synthetic.py --clean            # no injected problems
```

| File | What's in it |
|---|---|
| `data/synthetic_requests.csv` | 80 invented requests from 4 teachers (`T1`–`T4`) plus 1 duplicate, same columns as the sheet |
| `data/synthetic_year.csv` | 400 requests over 12 months, for the seasonality metric (busier Sep 15 – Oct 15, quieter from late November) |
| `*.issues.json` | IDs of rows with deliberate problems (duplicate ID, dates out of order, a stage after Lost) that `validate.py` must catch |

The same seed always gives the same file. No names or contact details are generated.
