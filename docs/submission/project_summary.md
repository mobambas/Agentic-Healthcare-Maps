# Project summary (Hack-Nation upload)

**Lakshmi** is an ASHA worker in a rural block where families still travel hours for care, only to find the listed hospital lacks the specialist or equipment they were promised. Challenge 03 asks for a **reasoning layer** on messy facility text—not another static directory.

This project is a **deployable extraction and validation pipeline** that runs on **commodity hardware** using **open-weight** models (**Qwen 2.5 7B Instruct** served via **vLLM** on **Google Colab Pro**), sized for the **10,000+** facility audit the brief describes—**without** per-call frontier API economics that would make NGO and government-scale rollout infeasible. The **30-record** human gold set extracted with **Anthropic Sonnet 4.6** is retained as a **frontier-model reference slice** for comparison; **production** batching targets **$0 marginal API cost** for full-corpus extraction on rented GPU time.

Structured claims feed an **IPHS-grounded validator** (**17 rules** distilled from **IPHS 2022 Volumes I–IV**), a **conformal-calibrated trust scorer** (**92.86%** empirical coverage on the 30-record gold set against a **0.90** nominal target), and a **citation API** so every badge ties back to evidence text and rule IDs. On the gold validation sample, **8 of 101** capability-level checks triggered rule hits—most visibly **HIGH**-severity **R01/R02** surgical staffing and OT evidence gaps, plus **R33** emergency / ambulance linkage and **R09** obstetric readiness signals where claims outrun evidence.

The product stance is deliberately **asset-based**: the system **augments** ASHA workers and NGO planners with triage-grade audit signals—it does **not** replace frontline judgment or clinical decision-making.
