# BD Workspace

A local Windows workspace for product discovery, business development, source analysis and opportunity/principal reports.

## التثبيت مرة واحدة

1. [تنزيل النسخة 2.0.1](https://raw.githubusercontent.com/engaliasiri2012-lab/bd-workspace-updates/main/releases/BD-Workspace-Setup-2.0.1.zip).
2. أوقف النسخة القديمة بـ Ctrl+C في نافذة التشغيل، ثم فك ضغط الملف الجديد بالكامل.
3. افتح مجلد BD-Workspace. اضغط Alt+D، اكتب `cmd` ثم Enter.
4. اكتب `py -3 install.py` ثم Enter.
5. استخدم اختصار **BD Workspace** على سطح المكتب لاحقًا.

يتطلب Python 3.10 أو أحدث. تبقى بيانات النسخة السابقة في `%LOCALAPPDATA%\MidadBDWorkspace`، ويُثبت البرنامج في `%LOCALAPPDATA%\MidadBDApp`. يستخدم التثبيت الجديد البيانات القديمة تلقائيًا عند استخدام مسار البيانات الافتراضي. التثبيت لأول مرة على جهاز جديد يبدأ بدليل شركات فارغ، ويمكن رفع مصادرك من داخل التطبيق.

## التحديثات التالية

من **الإعدادات والنسخ ← التثبيت والتحديثات** اضغط **البحث عن تحديث** ثم **تثبيت التحديث**، وبعد اكتماله **إعادة التشغيل للتفعيل**. عنوان النشر مدمج. لن تحتاج إلى تنزيل النسخة كاملة يدويًا كل مرة.

للنسخة 2.0.0 التي تتضمن صفحة التحديثات بالفعل، احفظ هذا الرابط في مصدر التحديث مرة واحدة ثم ابحث عن تحديث:

https://raw.githubusercontent.com/engaliasiri2012-lab/bd-workspace-updates/main/latest.json

البرنامج يتحقق من بصمة SHA-256، ويحفظ نسخة SQLite قبل التحديث، ويبقي الإصدار السابق للرجوع إليه. التحديثات تحتاج ضغطة زر؛ لا يجري تثبيت كود جديد بصمت. يلزم إدخال مفتاح API مجددًا بعد إعادة تشغيل البرنامج لأنه يبقى في الذاكرة فقط.

## Features

- Arabic/English interface, existing CRM-style records and saved research.
- Web plus selected source text, restricted website domains, or selected text only.
- Editable company comparison with 61 fields and evidence for each assessment.
- Filters for distinctive technology, international awards, no Saudi presence found, and Aramco technical product approval, combined with ALL or ANY logic.
- Aramco vendor registration and trials are distinct from product approval. No presence found is not proof of absence or an available exclusive territory.
- Local drag-and-drop PDF, PPTX, XLSX, DOCX, TXT, CSV and Markdown intake, duplicate detection, then optional AI analysis with consent.
- Excel/CSV comparison, Word report, concise or detailed editable PowerPoint, browser print-to-PDF preview.

## Limits and data

Your database, attachments and API key are not part of this public repository or its downloads. Files stay local until you explicitly select source text and consent to an AI request. OpenAI API calls have separate usage charges; company discovery uses research and a formatting request. No live paid API requests were used for development tests.

Text extraction does not include OCR, images, diagrams or PowerPoint speaker notes. XLSX uses cached formula results. File limit: 10 MB each. Source text: up to 50,000 characters per selected source and 100,000 combined. Longer material must be split or narrowed.

PowerPoint headings are English; findings retain their research language. Summary slides abbreviate long fields. Detailed reports preserve the full available fields. Generated contact details and commercial findings require source review. Scores are provisional assessments, not certifications. GP calculation uses TAM × share × margin only with sufficient inputs.

A backup downloaded from Settings includes records and attachments. The pre-update SQLite snapshot covers the database; updates do not modify existing attachments. Rollback switches code only. New releases must preserve database compatibility or include a tested migration.

## Development and publishing

```sh
python -m pip install -r requirements.txt --target vendor
python -m unittest -v test_app test_features test_updater
python publishing/build_release.py --notes "Release notes"
```

Update VERSION first. Commit the source, generated update ZIP, installer ZIP and latest.json together. Packages use immutable version names. The build excludes supplied source files and always includes an empty supplier seed. Future maintainers: read AGENTS.md before publishing.

The app binds only to 127.0.0.1. The optional personal installer creates a Windows shortcut. Actual shortcut behaviour and browser printing must be checked on Windows; Python, package integrity and update flows have been tested in the development environment.
