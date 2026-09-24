# Legal Disclaimer and Terms of Use

**UAE Business Setup Advisor**
Last updated: 2026-09-24 · Version 1.0

> **Summary.** An evidence-backed advisor for UAE business setup and renewal. This project is provided for **demonstration and testing purposes only**. It is **not** legal, tax, financial, immigration or business-setup advice, and its output is not a license, approval or official confirmation from any authority. All content is sample content. **All responsibility for any use of this software, and all legal and regulatory obligations arising from it, rests solely with the user.**

---

## 1. General Disclaimer

### 1.1 Not Professional Advice

This software — including its source code, command-line tools, APIs, user interfaces, documentation, rule files, data files, prompts, reports and any output it produces (together, the **"System"**) — is provided for general informational, educational and testing purposes only.

No content produced by or contained in the System:

- constitutes legal, tax, financial, immigration or business-setup advice;
- creates a lawyer–client, consultant–client or any other professional relationship;
- replaces the opinion of a qualified lawyer, tax adviser or licensed business-setup professional;
- may be used as the basis for any company formation, license application or renewal, tax registration, visa application, contract, investment or other legal or financial decision;
- constitutes evidence before any court, arbitral tribunal, mediator, regulator or administrative authority.

If you have a legal, tax or business-setup question, consult a licensed and qualified lawyer, tax adviser or licensed business-setup professional in the relevant jurisdiction.

### 1.2 Sample Content

All content in the System is **sample content only**, including:

- the seed records in `data/seed/` — laws, license types, required documents, fees, penalties, alternative documents, institutions, addresses, websites and phone numbers — compiled for development and **not verified** against official sources;
- the rule files in `config/rules/` and the response templates in `config/templates/`;
- examples in the documentation;
- setup plans, document lists, penalties and answers produced by the System.

None of it may be treated as definitive, current, complete or applicable to a specific situation, because:

- Company, licensing, tax and labor rules differ between countries, emirates, free zones, authorities and sectors;
- they are amended, replaced and repealed over time, and new laws, regulations, fee schedules and circulars are issued continuously;
- the facts of a specific case (product, parties, dates, location, sector) can fundamentally change the outcome;
- exceptions, exemptions and transitional provisions can override general rules.

### 1.3 Not an Official Confirmation

A result produced by the System — including a "New Setup Plan" or a "Renewal Assessment" — is not a license, approval, clearance or official confirmation. Fees, penalties and document requirements shown are sample values and may be wrong or outdated. An abstention message does **not** mean that a human expert will review the case: the escalation queue is a local file that exists for demonstration only.

The System is independent and is not affiliated with, endorsed by, sponsored by or connected to Dubai Economy and Tourism (DET), the Abu Dhabi Department of Economic Development (ADDED), any free zone authority (including DMCC, IFZA, Meydan Free Zone, JAFZA, DIFC, ADGM, RAKEZ and DAFZA), the Federal Tax Authority (FTA), the Ministry of Human Resources and Emiratisation (MOHRE), the Federal Authority for Identity, Citizenship, Customs and Port Security (ICP), the Dubai Land Department, or any other government authority, regulator, free zone, standards body or company. Names of authorities, laws and standards are used for identification and reference only.

### 1.4 The User Is Solely Responsible

Every natural or legal person who uses the System (the **"User"**):

- must independently verify the accuracy, currency, completeness and applicability of any information, finding, classification, checklist, document list or answer obtained from the System, directly with the relevant authority;
- is **solely, entirely and irrevocably responsible** for:
  - all decisions made with or without the System;
  - all legal, regulatory, administrative, criminal, financial and commercial consequences of those decisions;
  - all obligations towards authorities, free zones, landlords, employees, shareholders, customers and any other third party;
  - all actions taken or omitted in reliance on the System's output.

### 1.5 Disclaimer of Liability

To the maximum extent permitted by applicable law, the authors, contributors, licensors and distributors of the System (the **"Developers"**) shall not be liable, under any legal theory (contract, tort, negligence, strict liability, product liability, statute or otherwise), for any loss or damage — direct, indirect, incidental, special, punitive or consequential — arising from:

- the use of, or inability to use, the System;
- errors, omissions, inaccuracies or outdated content in the System;
- any action taken or not taken in reliance on the System's output;
- any fine, penalty, license suspension or cancellation, rejected application, tax liability or visa issue;
- the integration of third-party services (LLM APIs, vector databases, cloud providers);
- data loss, data breaches, unauthorized access or service interruption;
- the interpretation of the System's output by the User or by third parties.

---

## 2. Risks Specific to Artificial Intelligence

### 2.1 Large Language Models

By default the System is deterministic and does not use a language model. If the User configures an OpenAI API key, a large language model is used as a fallback to map unusual phrasing onto the System's fixed vocabularies. Large language models:

- can **hallucinate** — produce fabricated but persuasive content, including non-existent rules, clauses or citations;
- can reflect **biases** in their training data;
- can produce **outdated** information;
- can **guess** instead of expressing uncertainty;
- can perform **inconsistently** across languages, in particular with Arabic regulatory terminology;
- can cite sources **out of context** or **incorrectly**.

### 2.2 Safeguards and Their Limits

The System includes the following safeguards:

- **Source-bound claims** — every statement is bound to a database record by a SHA-256 content hash;
- **Three-stage verification** — schema, existence + hash, effective window;
- **Template-based answers** — every sentence comes from a template; the model never writes user-facing text;
- **Vocabulary-constrained LLM fallback** — model output outside fixed vocabularies is discarded;
- **Abstention** — missing facts or records lead to a question or an abstention instead of a guess;
- **Explicit state machine** — no step can be skipped.

**These safeguards reduce risk; they do not eliminate it:**

- verification confirms that a statement matches a record in the database — **not that the record is correct**;
- the seed records are unverified sample data and may be wrong, incomplete or outdated;
- keyword-based classification can misread a request and choose the wrong structure, emirate or activity;
- rule and template files are written by humans and can contain errors;
- the escalation queue is a local file; no human reviews escalated cases.

**No output of the System may serve as the basis for any legal, tax, financial or business decision without review by a qualified professional.**

### 2.3 Acceptance of AI-Related Risks

By using the System, the User acknowledges that AI-assisted and rule-based output is inherently uncertain and may contain errors, agrees not to rely on it as the sole basis for any decision, assumes all risk for decisions based on it, and — to the maximum extent permitted by law — waives any claim against the Developers arising from such errors.

---

## 3. Data, Third-Party Services and Privacy

### 3.1 Data Sources

The seed records in `data/seed/` were compiled from public information for development and demonstration. The System does not connect to any official source and does not download laws or fee schedules. Addresses, websites and phone numbers may be outdated.

The Developers do not guarantee that any data in the System is accurate, current or complete, or that it matches any official text.

### 3.2 Third-Party Services

If configured, the System uses the **OpenAI API** for its optional classifier fallback. The API and web interface run locally.

These services are subject to their own terms of use, privacy policies and data processing terms. The Developers are not responsible for the acts, omissions, outages or data breaches of any third-party service, and any data sent to them is sent at the User's own responsibility.

### 3.3 Privacy and Data Protection

When an OpenAI API key is configured, the text of the User's request may be sent to the third-party provider. The System stores escalated requests, including their full text, in `records/escalations.jsonl`.

The User:

- **must not** enter personal, sensitive or confidential data, including passport or Emirates ID numbers, names of shareholders, trade secrets or financial information;
- must anonymize any real data before using it with the System;
- is responsible for securing all files the System writes locally (`records/escalations.jsonl` and any database file);
- is solely responsible for compliance with applicable data protection laws, including UAE Federal Decree-Law No. 45 of 2021 (PDPL), the Saudi Personal Data Protection Law and the EU GDPR where applicable.

The Developers give **no warranty** of compliance with any data protection law.

---

## 4. Sample Scenarios and Test Cases

Examples in the documentation, golden test cases and sample requests are **fictional**. They do not describe any real person, company or application and cannot be used to resolve a real case.

---

## 5. Intellectual Property and License

- The System's source code is distributed under the **MIT License** — see [LICENSE](LICENSE).
- Names of authorities, laws, standards, products and services mentioned in the System belong to their respective owners and are used for identification only.
- Official regulatory texts, their translations, compilations and commentaries may be subject to their own copyright and terms of use.
- Anyone who copies, modifies, redistributes or integrates the System, including for commercial purposes, must keep this disclaimer with it.

---

## 6. Warranty Disclaimer

The System is provided **"as is"** and **"as available"**, without warranty of any kind, express or implied, including warranties of merchantability, fitness for a particular purpose, accuracy, non-infringement, uninterrupted operation, or that errors will be corrected.

---

## 7. Limitation of Liability

To the maximum extent permitted by applicable law, the Developers' aggregate liability for all claims arising from or related to the System is limited to the amount the User paid for the System. The System is provided free of charge; where nothing was paid, the Developers' liability is **zero**.

---

## 8. User Undertakings

By using the System, the User undertakes:

1. not to use the System's output as legal, tax, financial, immigration or business-setup advice;
2. not to form a company, apply for or renew a license, register for tax or take any other legal or financial action based on the System's output without review by a qualified professional;
3. to use the System for demonstration, education, research or testing only;
4. not to enter personal, sensitive or confidential data;
5. not to use the System for any unlawful purpose;
6. to accept the consequences of any errors in the System's output;
7. to keep this disclaimer with any copy or derivative of the System;
8. to have read, understood and accepted this disclaimer.

---

## 9. Governing Law and Jurisdiction

This disclaimer and any dispute arising from the use of the System are governed by the laws of the United Arab Emirates as applied in the Emirate of Dubai. The courts of Dubai have exclusive jurisdiction, unless mandatory law provides otherwise.

If any provision of this disclaimer is held invalid or unenforceable, it shall be limited to the minimum extent necessary, and the remaining provisions shall remain in full force and effect.

---

## 10. Changes

The Developers may amend this disclaimer at any time without notice. Changes take effect when published in this repository. Continued use of the System constitutes acceptance of the amended disclaimer.

---

## 11. Contact

Questions about this disclaimer can be raised through the repository's issue tracker: https://github.com/Alicanefee/UAE-Business-Setup-Advisor/issues

---

## Final Word

This System is a **tool** for demonstration and testing. It is **not** a government authority, a free zone, a business-setup agent, a tax adviser, a law firm or a lawyer. It does **not** protect you from legal liability — **all responsibility arising from its use rests with you.**

*By using the System, you confirm that you have read, understood and accepted this disclaimer.*
