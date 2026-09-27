# BD Workspace release maintenance

This is a public code and update distribution repository for a personal local Windows app.

- Never commit user source documents, supplier/company records, databases, attachments, real API keys, authentication credentials or update-settings.json.
- `seed/suppliers.json` must remain `[]`. The user's existing SQLite records are reused on their laptop, never synced here.
- Private source references must be uploaded by the user locally, never bundled into a public package.
- Keep the default feed URL `https://raw.githubusercontent.com/engaliasiri2012-lab/bd-workspace-updates/main/latest.json` stable.
- Publish source and packages together in a single fast-forward commit. Never force-push, rewrite prior releases or reuse a version number.
- Before changes inspect current main and relevant instructions. Preserve unrelated changes.
- For an update, increment VERSION, run meaningful affected tests, then run `python publishing/build_release.py --notes "..."`.
- Both `releases/bd-X.Y.Z.zip` and `releases/BD-Workspace-Setup-X.Y.Z.zip` and latest.json must be committed together.
- Verify the live public manifest and SHA-256 of the downloaded package after publication.
- Test preservation of existing user data. Rollback switches application code only, so schema changes need a compatible migration design.
- `vendor/` is a local build dependency installed using requirements.txt and bundled in release ZIPs; do not commit it separately.
- Never spend the user's API funds for a test without authorization. Mock API response handling and disclose live-test limitations.
- Core tests run with `python -m unittest -v test_app test_features test_updater`.
