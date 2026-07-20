# Stage form workflow

## Lifecycle

1. From the repository checkout, run `"$FORMS" sync`, where `FORMS` is the installed
   plugin's `scripts/forms.py`.
2. Give the returned `answers/<stage>.md` path to the user.
3. Wait for the user to edit the file and say `작성 완료`.
4. Run `"$FORMS" status` and read the current form.
5. Ask one follow-up only when an answer is ambiguous, contradictory, unsafe to
   structure, or required by a server gate but absent.
6. Write conservative workflow `extracted` JSON to `answers/.extracted.json` and run:

   ```bash
   "$FORMS" submit --extracted-file answers/.extracted.json
   ```

7. Run `"$FORMS" sync`. If the gate passes, advance once and sync the next form.

## Ownership and safety

- The user owns the answer text outside the generated server-state block.
- Form sync may update YAML `status` and the generated state block only.
- Never overwrite an existing form from the template.
- Do not create future-stage forms early.
- Do not submit a form for a stage other than the server's current stage.
- Do not submit when required headings are empty.
- An unchanged second submission is a no-op. A changed submitted form becomes a
  clarification claim; it does not silently replace prior evidence.
- A successful submission deletes the temporary `.extracted.json`; a failed one keeps
  it for correction.
- The fingerprint excludes YAML, comments, and generated server state so sync does not
  make an unchanged form appear revised.
- Do not embed customer secrets or unmasked records. The files persist under the
  repository's ignored `answers/` directory until deleted by the operator.

## CLI response examples

At stage start:

```text
현재 단계 양식을 준비했습니다: answers/01-inception.md
파일을 작성한 뒤 “작성 완료”라고 알려주세요.
```

For missing content:

```text
아직 “측정 가능한 성공 기준”이 비어 있습니다.
같은 파일에 성공 여부를 판단할 수치나 관찰 기준을 추가해주세요.
```

Do not paste every heading or repeat the entire questionnaire in the terminal.
