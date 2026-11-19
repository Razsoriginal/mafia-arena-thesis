# Search log (Phase R, 2026-11-12)

Three parallel research passes plus one adversarial citation check. Each section is the raw log of one pass. Searches were web search + page fetch; no paid API calls; no personal data in queries.


## Search log: agentic irreversible-action incidents

| query | date searched | source | relevance | note |
|---|---|---|---|---|
| PocketOS Railway Cursor agent deleted production database backups | 2026-11-12 | web search (Computing, heise, TechRadar, PC Gamer, AIID r7167, Decrypt) | high | Lead found; many secondary sources |
| (fetch) incidentdatabase.ai/reports/7167 | 2026-11-12 | AIID | high | Incident 1469; Cursor + Claude Opus 4.6 per founder |
| Railway blog PocketOS incident delayed delete legacy endpoint Jake Cooper | 2026-11-12 | web search (Tom's Hardware, Register mirror, NeuralTrust) | high | Cooper statement via The Register |
| railway.com blog post-mortem volume deletion agent API token April 2026 | 2026-11-12 | web search -> railway.com/changelog/2026-05-01-undoable-deletes | high | Provider primary found |
| (fetch) theregister.com 2026/04/27 cursoropus_agent_snuffs_out_pocketos | 2026-11-12 | The Register | high | Gives founder X URL, confession quotes, Railway statements |
| (fetch) railway.com changelog undoable-deletes | 2026-11-12 | Railway (primary) | high | Confirms incident class and 48 h soft-delete fix |
| (fetch) blog.railway.com/p/your-ai-wants-to-nuke-your-database | 2026-11-12 | Railway (primary) | high | Token found locally, account-scoped, volumeDelete, data recovered; no customer/model named |
| (fetch) x.com/lifeof_jer/status/2048103471019434248 | 2026-11-12 | X | none | HTTP 402, not retrievable |
| Replit agent deleted SaaStr production database Jason Lemkin code freeze | 2026-11-12 | web search (AIID 1152, TechTarget, Fortune, eWeek, Gizmodo) | high | Lead found |
| (fetch) incidentdatabase.ai/cite/1152 | 2026-11-12 | AIID | high | Date 2025-07-18; Lemkin X URL |
| saastr.com Lemkin Replit deleted database vibe coding day 9 lessons | 2026-11-12 | web search | med | No saastr.com primary on the deletion found |
| (fetch) theregister.com 2025/07/21 replit_saastr_vibe_coding_incident | 2026-11-12 | The Register | high | Lemkin X post URLs, rollback worked |
| Amjad Masad x.com Replit ... "unacceptable and should never be possible" | 2026-11-12 | web search (BI, Fortune, eWeek) | med | CEO statement and fixes via secondary only |
| Gemini CLI deleted user files "I have failed you completely and catastrophically" anuraag | 2026-11-12 | web search (AIID, Slashdot, Yahoo/Mashable) | high | Lead found |
| (gh api) google-gemini/gemini-cli issue 4586 | 2026-11-12 | GitHub (primary) | high | Created 2025-07-21 by anuraag2601 |
| Anuraag Gupta blog Gemini CLI deleted files post mortem move command Windows | 2026-11-12 | web search | high | Post URL anuraag2601.github.io/gemini_cli_disaster.html |
| (fetch) anuraag2601.github.io/gemini_cli_disaster.html | 2026-11-12 | author blog | none | 404 now |
| (fetch) Ars Technica 2025/07 ai-coding-assistants-chase-phantoms (reader mirror) | 2026-11-12 | Ars Technica | high | Mechanism (Windows move rename/overwrite) |
| Amazon Q Developer extension malicious prompt wiper 1.84 AWS security bulletin AWS-2025-015 | 2026-11-12 | web search | high | Bulletin located |
| (fetch) aws.amazon.com/security/security-bulletins/AWS-2025-015 | 2026-11-12 | AWS (primary) | high | Scoped-token root cause, payload did not execute, CVE-2025-8217 |
| Google Antigravity deleted entire D drive turbo mode reddit | 2026-11-12 | web search (Register, Tom's HW, AIID 7051) | high | Lead found |
| (fetch) theregister.com 2025/12/01 google_antigravity_wipes_d_drive | 2026-11-12 | The Register | high | Reddit/YouTube URLs, Gemini 3, Google statement |
| Financial Times AWS Kiro AI agent outage delete and recreate environment Amazon rebuttal | 2026-11-12 | web search (PC Gamer, Register, Engadget, the-decoder) | high | FT date 2026-02-20 |
| aboutamazon.com response Financial Times Kiro AWS Cost Explorer outage | 2026-11-12 | web search | high | Amazon rebuttal located |
| (fetch) aboutamazon.com/news/aws/aws-service-outage-ai-bot-kiro | 2026-11-12 | Amazon (primary) | high | "user error ... not AI"; peer review added |
| Claude Code rm -rf ~/ deleted home directory github issue | 2026-11-12 | web search (claudeissues.com mirror, Docker blog, dev.to) | high | Many issue numbers |
| (gh api) anthropics/claude-code issues 10077, 12637, 36339 | 2026-11-12 | GitHub (primary) | high | All three verified; all closed not_planned |
| Invariant Labs GitHub MCP toxic agent flow private repository exfiltration | 2026-11-12 | web search | high | Demo |
| (fetch) invariantlabs.ai/blog/mcp-github-vulnerability | 2026-11-12 | Invariant (primary) | high | 2025-05-26, Claude 4 Opus, demo repos |
| Claude Code terraform destroy deleted production DataTalks.Club database Alexey Grigorev | 2026-11-12 | web search (AIID 1424, Tom's HW) | high | New incident |
| (fetch) alexeyondata.substack.com -> aishippingblog.com how-i-dropped-our-production-database | 2026-11-12 | author (primary) | high | Full post-mortem |
| Supabase MCP prompt injection service_role leak integration_tokens General Analysis | 2026-11-12 | web search | high | Demo |
| (fetch) generalanalysis.com/blog/supabase-mcp-blog | 2026-11-12 | General Analysis (primary) | high | 2025-07-08 demo, dummy data |
| Brave Perplexity Comet indirect prompt injection account takeover email OTP disclosure | 2026-11-12 | web search | high | Demo |
| (fetch) brave.com/blog/comet-prompt-injection | 2026-11-12 | Brave (primary) | high | Timeline 2025-07-25 to 2025-08-20 |
| OpenAI Operator bought eggs without permission Washington Post Fowler | 2026-11-12 | web search (AIID 1028, ADN syndication) | high | Unauthorised purchase |
| OpenClaw agent deleted inbox emails Summer Yue Meta "confirm before acting" | 2026-11-12 | web search | high | New incident |
| (fetch) incidentdatabase.ai/cite/1542 | 2026-11-12 | AIID | high | Date 2026-02-23 |
| (fetch) businessinsider.com meta-ai-alignment-director-openclaw-email-deletion | 2026-11-12 | Business Insider | none | Fetch blocked |
| AI coding agent force push deleted git history repository incident 2025 Cursor YOLO mode deleted files | 2026-11-12 | web search | high | Found Cursor forum, geextor, 48k-file case |
| (fetch) forum.cursor.com t/91573 | 2026-11-12 | Cursor forum (primary) | med | Single uncorroborated user post |
| (fetch) geextor.com 2025/08/21 (reader mirror) | 2026-11-12 | author blog (primary) | med | Force-push history wipe |
| (fetch) incidentdatabase.ai/cite/1719 | 2026-11-12 | AIID | med | 48k files, single TechRadar report, unverified |
| (fetch) techradar.com i-broke-something ... 48-000-files | 2026-11-12 | TechRadar | low | Truncated content |
| (fetch) incidentdatabase.ai/cite/1424 | 2026-11-12 | AIID | high | Links author post |
| AI Village agent sent unsolicited email Rob Pike December 2025 Claude Opus | 2026-11-12 | web search (Willison, Gizmodo) | med | Unsolicited outbound email case |
| EchoLeak CVE-2025-32711 Microsoft 365 Copilot zero-click Aim Security exfiltration | 2026-11-12 | web search (THN, TechRepublic) | med | Vulnerability; MSRC/Aim not fetched |

## Search log: abstention / calibrated deferral prior art

| Query | Date searched | Source | Relevance | Note |
|---|---|---|---|---|
| arxiv.org/abs/2607.10059 (direct) | 2026-11-12 | arXiv abs + HTML | high | AgentAbstain confirmed; read methods/results/limitations (partial HTML) |
| arxiv.org/abs/2606.02965 (direct) | 2026-11-12 | arXiv abs + HTML | high | Now titled "Designing for Doubt", AIES 2026; v1 title "What Benchmarks Don't Measure" |
| "What Benchmarks Don't Measure" agents abstention compliance bias | 2026-11-12 | web search | high | Confirms v1 title via chatpaper/newx listings; AAAI OJS version |
| arxiv.org/abs/2602.16666 (direct) | 2026-11-12 | arXiv abs + HTML | high | Rabanser et al., ICML 2026; 12 metrics; no AURC |
| SteerBench-Work proceed or hold false-hold agent benchmark | 2026-11-12 | web search | high | Found arXiv:2608.12654 |
| arxiv.org/abs/2608.12654 (direct) | 2026-11-12 | arXiv abs | high | 28.1% wrongly hold vs 1.0% wrongly allow |
| AbstentionBench reasoning LLMs fail on unanswerable questions arXiv | 2026-11-12 | web search + arXiv HTML | high | 2506.09038; reasoning degrades abstention ~24% |
| exformation LLM arXiv | 2026-11-12 | web search | none | No hits using the term |
| arxiv "exformation" language model OR agents | 2026-11-12 | web search (extended) | none | No hits |
| export.arxiv.org API search_query=all:exformation | 2026-11-12 | arXiv API | none | 3 results, all EXFormer/transformer false matches |
| exformation "large language models" omission unsaid 2025 OR 2026 | 2026-11-12 | web search (extended) | med | Found omission papers 2610.11351, 2512.01728; none use "exformation" |
| "exformation" Nørretranders artificial intelligence communication paper | 2026-11-12 | web search | low | Only concept origin (Nørretranders), no AI paper |
| api.semanticscholar.org search exformation | 2026-11-12 | Semantic Scholar API | n/a | HTTP 429, not checked; gap to close later |
| "typesafe/jev" OR "Jev System-One" model gate | 2026-11-12 | web search | med | Vendor/gateway pages (Zuplo, OrcaRouter); launch ~2026-09-15 |
| arxiv TypeSafe Jev calibrated "System One" paper | 2026-11-12 | web search | high | Found 2609.24052, 2609.37647 |
| Jev System One model arXiv 2026 abstention calibration agent gate evaluation | 2026-11-12 | web search (extended) | high | Found 2609.33401, 2609.26532, 2609.35342, 2610.19811, 2610.18773, 2609.29429 (via system-one-guard repo) |
| arxiv.org/abs/2609.33401, 2609.37647, 2609.24052, 2609.26532, 2609.29429, 2609.35342 (direct) | 2026-11-12 | arXiv abs | high | Abstracts read; Jev literature >= 8 papers |
| Robots that ask for help KnowNo conformal prediction LLM planner | 2026-11-12 | web search | high | 2307.01928, CoRL 2023; 10-24% less help |
| UALA uncertainty-aware language agent arXiv | 2026-11-12 | web search | med | 2401.14016, ACL Findings 2024 |
| conformal risk control LLM agent action abstention irreversible 2026 arXiv | 2026-11-12 | web search (extended) | high | CORA 2604.09155, CSA 2605.20270, Role-Stratified CRC 2607.24343, ToolChain-CRC 2606.18467 |
| arxiv.org/abs/2604.09155, 2605.20270 (direct) | 2026-11-12 | arXiv abs | high | CORA irreversible GUI actions; CSA anytime-valid act/abstain |
| LLM agents ask clarifying questions before acting benchmark underspecified 2025 2026 | 2026-11-12 | web search (extended) | med | Ask or Assume 2603.26233 (EMNLP 2026), Ask2Decide 2611.13015, 2606.19559, 2604.14624 |
| arxiv.org/abs/2603.26233 (direct) | 2026-11-12 | arXiv abs | med | 69.40% vs 70.80% |
| Werewolf Mafia LLM agents deception vote calibration abstain lynch benchmark | 2026-11-12 | web search (extended) | high | WOLF 2512.09187, MafiaScope 2607.10645, Triadic Werewolf 2606.27909 |
| arxiv.org/abs/2512.09187, 2607.10645 (direct) | 2026-11-12 | arXiv abs | high | No abstain/no-lynch evaluated in either |
| LLM social deduction game abstain vote "no lynch" OR "skip vote" uncertainty calibrated agent | 2026-11-12 | web search | med | Jury theorem 2602.22413; Werewolf RL 2310.18940 allows abstain; CSP4SDG 2511.06175 |
| arxiv.org/abs/2602.22413 (direct) | 2026-11-12 | arXiv abs | med | Confidence-gated vote/abstain theory |
| say-do gap LLM agents stated versus revealed behavior consistency arXiv | 2026-11-12 | web search (extended) | med | 2611.10628, 2606.00476, 2506.00751, 2507.02197, 2604.09189 |
| arxiv.org/abs/2611.10628 (direct) | 2026-11-12 | arXiv abs | med | Term "say-do gap" not on abs page |
| default mode network task-positive network inspired LLM agent architecture arXiv | 2026-11-12 | web search | low | Only 2507.19495 (mind-wandering module) |
| AIWILD 2026 Mafia DMN TPN exformation Fractal Cerebral | 2026-11-12 | web search | none | Source paper not found publicly |
| Know Your Limits survey abstention LLMs Wen 2024 TACL | 2026-11-12 | web search | med | 2407.18418, TACL 2025 |
| LLM agent irreversible actions benchmark over-caution over-refusal agents tool use 2026 | 2026-11-12 | web search (extended) | high | SentryBench 2610.34535, take-my-word repo, refusal transfer 2610.28982, Saber 2606.01317 |
| arxiv.org/abs/2610.34535, github.com/tokenrip/take-my-word (direct) | 2026-11-12 | arXiv abs / GitHub | high | Over-refusal 100% under refuse-more; take-my-word pilot not preregistered |
| selective prediction LLM risk-coverage AURC benchmark confidence-gated 2025 2026 | 2026-11-12 | web search | med | 2607.03528, 2603.21172, 2604.03216, 2604.17716; AURC orientation varies |
| arxiv.org/abs/2609.07395 (direct) | 2026-11-12 | arXiv abs | med | TC-ECE; no AURC |
| LLM learning to defer to human expert calibrated deferral agents 2025 2026 arXiv | 2026-11-12 | web search | low | L2D cluster (2602.17144, 2603.14324, 2608.05064, 2604.08588); not agentic-irreversible |
| pre-registered evaluation LLM agents abstention random baseline null floor compute-matched self-consistency | 2026-11-12 | web search | med | No pre-registered abstention study found; Agentic Abstention 2606.28733; TrACE 2604.08369 compute-matched SC |
| neurips.cc poster 139558; arxiv.org/abs/2606.28733 (direct) | 2026-11-12 | NeurIPS / arXiv | high | AgentAbstain NeurIPS 2026 oral session; Agentic Abstention NeurIPS 2026 |

## Search log: agent safety prior art

All searches and fetches were run on 2026-11-12, through a web search tool and a page fetcher that summarises each page. "Fetch" means a specific URL was retrieved and read.

| query | date searched | source | relevance | note |
|---|---|---|---|---|
| ToolEmu identifying risks of LM agents with an LM-emulated sandbox arXiv | 2026-11-12 | web search (arXiv, ICLR, NeurIPS) | high | 2309.15817, ICLR 2024; 36 toolkits / 144 cases; 23.9% failure rate for the safest agent |
| Agent-SafetyBench evaluating safety of LLM agents arXiv 2412 | 2026-11-12 | web search (arXiv) | high | 2412.14470 v2; 349 envs, 2,000 cases; no agent scores above 60% |
| OpenAgentSafety benchmark real-world agent safety 2025 arXiv | 2026-11-12 | web search (arXiv, ICLR 2026) | high | 2507.06134; real tools in Docker; 49–73% unsafe |
| benchmark LLM agent destructive irreversible operations database DevOps delete production | 2026-11-12 | web search (extended) | high | Found DBA-Bench, SABER, SNARE, LITMUS; incident blogs (Replit/SaaStr, terraform destroy) are low-trust |
| fetch arxiv.org/abs/2607.22165 (DBA-Bench) | 2026-11-12 | arXiv abs | high | v2 Oct 2026; 231 + 10 scenarios on live PostgreSQL/TiDB; no numbers on the abs page |
| fetch arxiv.org/abs/2606.01317 (SABER) | 2026-11-12 | arXiv abs | med | EMNLP 2026; HSR >54% for the best model |
| fetch arxiv.org/abs/2605.28122 (SNARE) | 2026-11-12 | arXiv abs | med | 19.51% overeager; framework explains 56% of variance |
| fetch arxiv.org/abs/2605.10779 (LITMUS) | 2026-11-12 | arXiv abs | high | Execution Hallucination, prior art for the say-do gap; 40.64% for Sonnet 4.6 |
| AgentHarm benchmark harmfulness LLM agents benign counterparts arXiv 2410.09024 results | 2026-11-12 | web search (arXiv, Gray Swan) | high | ICLR 2025; harmful/benign pairs; synthetic tools |
| agent over-refusal benchmark paired benign harmful tool tasks should act should abstain 2025 2026 | 2026-11-12 | web search (extended) | high | Found Refusal-Transfer 2610.28982, SentryBench 2610.34535, BioSecBench-Refusal, MOSAIC 2603.03205 |
| InjecAgent ... ; AgentDojo ... results | 2026-11-12 | web search | med | No numbers in the snippets; firewall paper 2510.05244 and AgentDyn 2602.03117 noted (not read) |
| R-Judge ...; SafeAgentBench ... rejection rate | 2026-11-12 | web search (arXiv, ACL Anthology) | high | R-Judge 74.45% (v3); SafeAgentBench safety prompt over-refuses >40% of safe tasks |
| fetch arxiv.org/abs/2403.02691 (InjecAgent) | 2026-11-12 | arXiv abs | med | 1,054 cases; ReAct GPT-4 ASR 24% |
| fetch arxiv.org/abs/2406.13352 (AgentDojo) | 2026-11-12 | arXiv abs | med | 97 tasks / 629 cases; abs page has no numbers or venue |
| fetch alphaxiv.org/abs/2610.28982 (Refusal transfer) | 2026-11-12 | alphaXiv abs | high | Matched harmful/benign triplets; 10–52% divergence; calls not executed |
| fetch arxiv.org/abs/2610.34535 (SentryBench) | 2026-11-12 | arXiv abs | high | Trust-gating wrapper beats refuse-more prompting on harm |
| SHADE-Arena sabotage monitoring LLM agents arXiv 2506.15740 results | 2026-11-12 | web search (arXiv) | med | About 27% undetected sabotage; monitor AUC 0.87 |
| ST-WebAgentBench ...; MobileSafetyBench results | 2026-11-12 | web search | med | CuP below 2/3 of completion; no MobileSafetyBench numbers |
| RedCode benchmark risky code execution ... rejection rate | 2026-11-12 | web search (NeurIPS, Microsoft) | med | Design confirmed; per-model numbers not found |
| tau-bench safety policy violation variant ... tau2 safety | 2026-11-12 | web search | med | No official τ safety variant; τ-break (2506.09600); symbolic guardrails 2604.15579 |
| fetch arxiv.org/abs/2604.15579 (Symbolic guardrails) | 2026-11-12 | arXiv abs | high | 85% of 80 benchmarks lack verifiable requirements; 74% of requirements enforceable |
| fetch arxiv.org/abs/2410.17520 (MobileSafetyBench) | 2026-11-12 | arXiv abs | low | No numbers; a prompting mitigation is only partial |
| AgentSpec ... ; ShieldAgent ... | 2026-11-12 | web search (arXiv) | high | AgentSpec ICSE 2026; o1 rules 95.56% precision / 70.96% recall |
| Progent ... AgentDojo ASR; CaMeL ... results | 2026-11-12 | web search (arXiv) | high | Progent 39.9%→1.0% ASR; CaMeL 77% vs 84% |
| GuardAgent ... EICU-AC Mind2Web-SC accuracy | 2026-11-12 | web search (ICML) | med | About 98% / 83%; secondary sources conflict |
| LlamaFirewall ... AgentDojo attack success reduction | 2026-11-12 | web search (press, aggregators) | med | 17.6%→1.75%; vendor self-evaluation |
| Anthropic agentic misalignment system prompt instruction ... blackmail rate reduced | 2026-11-12 | web search (press) | med | About 96%→37% with explicit rules, per a press chart; primary not read |
| fetch modelcontextprotocol.io/specification/2025-06-18/server/tools | 2026-11-12 | MCP spec (primary) | high | Human-in-the-loop SHOULD; annotations untrusted; audit logging |
| Invariant Labs guardrails policy language ...; NeMo Guardrails execution rails tool calling | 2026-11-12 | web search (vendor docs) | med | Invariant Gateway proxy rules; NeMo rails check content only |
| Werewolf Arena ...; AvalonBench LLM agents | 2026-11-12 | web search (arXiv, NeurIPS-W) | high | Win-rate-centred; no calibration or abstention |
| LLM Mafia game benchmark deception detection 2025; Among Us ...; Hoodwinked ... | 2026-11-12 | web search | high | Mini-Mafia, Hidden in Plain Text, MindGames, Among Us (NeurIPS 2025), Hoodwinked; board-game noise |
| WOLF werewolf benchmark ... calibration; MAgIC ... | 2026-11-12 | web search (arXiv, NeurIPS-W, EMNLP) | high | WOLF Brier/ROC suspicion; MAgIC multi-skill |
| LLM werewolf mafia agents vote abstention wrongful elimination calibrated uncertainty abstain 2026 | 2026-11-12 | web search (extended) | high | MafiaScope; QUACK/Abstention Inflation (EMNLP 2026, not verified); Conformal Social Choice |
| fetch arxiv.org/abs/2512.09187 (WOLF) | 2026-11-12 | arXiv abs | high | No vote accuracy, abstention or gating |
| fetch arxiv.org/abs/2509.23023 (Mini-Mafia) | 2026-11-12 | arXiv abs | med | Brier score is for the predictor, not agent calibration |
| fetch arxiv.org/abs/2607.10645 (MafiaScope) | 2026-11-12 | arXiv abs | high | Belief calibration vs engine ground truth; no numbers on the abs page |
| conformal act or escalate multi-agent debate wrong consensus EMNLP 2026 | 2026-11-12 | web search (ACL Anthology, arXiv) | high | 2604.07667; 81.9% of wrong-consensus errors intercepted |
| OWASP Top 10 for Agentic Applications 2026 list ASI01 tool misuse | 2026-11-12 | web search (secondary) | med | ASI01 Goal Hijack, ASI02 Tool Misuse; secondary only |
| fetch genai.owasp.org/llmrisk/llm062025-excessive-agency/ | 2026-11-12 | OWASP (primary) | high | Quotes on human approval, least privilege, downstream authorization |
| fetch genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ | 2026-11-12 | OWASP landing page | low | Date Dec 9 2025 only; the PDF was not read |
| NIST CAISI agent hijacking evaluations technical blog AgentDojo results 2025 | 2026-11-12 | web search (NIST, CSA) | high | Located the blog; red-teaming competition (250k attempts) noted |
| EU AI Act Article 14 human oversight text ... stop button | 2026-11-12 | web search | med | Paragraph numbering conflicts; resolved via the EC Service Desk fetch |
| CISA NCSC joint guidance AI agents agentic AI security 2025 2026 human approval least privilege | 2026-11-12 | web search (CSA, press) | med | Five Eyes "Careful Adoption of Agentic AI Services" |
| fetch content.govdelivery.com CISA bulletin 41544ff | 2026-11-12 | CISA bulletin (primary) | med | May 1 2026; co-authors; "broad or unrestricted access" |
| fetch ai-act-service-desk.ec.europa.eu/en/ai-act/article-14 | 2026-11-12 | European Commission (primary) | high | Art. 14(4)(a)–(e) excerpts |
| fetch nist.gov technical-blog-strengthening-ai-agent-hijacking-evaluations | 2026-11-12 | NIST (primary) | high | 11%→81% ASR; 57%→80% over 25 attempts |
| OWASP agentic top 10 2026 PDF least agency human-in-the-loop irreversible ASI02 mitigations | 2026-11-12 | web search (vendors) | low | Primary text still not reached |
| fetch cisa.gov/resources-tools/resources/careful-adoption-agentic-ai-services | 2026-11-12 | CISA (primary landing) | low | Summary only; the full guide was not read |
| NIST AI 600-1 ... human oversight agent; MITRE ATLAS AI agent techniques ... | 2026-11-12 | web search (secondary) | low | Secondary only; the profile is not agent-specific |
| OpenAgentSafety 2507.06134 benign vs adversarial intent unsafe rate ... | 2026-11-12 | web search (arXiv) | high | Benign intent 50–86% unsafe; hidden intent more than doubles the unsafe rate |
| LLM agent irreversible actions reversibility-aware benchmark confirmation before destructive tool call 2025 2026 | 2026-11-12 | web search (extended) | high | AgentAbstain, GateArena, UnderSpecBench, POLAR, StreamBench, AgentTrust, severity scale |
| system prompt safety rules vs external enforcement LLM agents empirical comparison ... | 2026-11-12 | web search | high | Mind the GAP 2602.16943; tool affordance 2603.20320; the rest are vendor blogs |
| fetch arxiv.org/abs/2607.10059 + html (AgentAbstain) | 2026-11-12 | arXiv abs + HTML (first 100k of 248k chars) | high | Paired act/abstain irreversible tools; no adversarial pressure, no gate baseline |
| fetch neurips.cc/virtual/2026/loc/sydney/168290 (GateArena) | 2026-11-12 | NeurIPS 2026 workshop page | high | Env-enforced confirmation; 91/400→0/400 |
| fetch arxiv.org/abs/2607.02294 (UnderSpecBench) | 2026-11-12 | arXiv abs | high | DevOps; 55.8–67.8% boundary violations |
| fetch arxiv.org/abs/2602.16943 (Mind the GAP) | 2026-11-12 | arXiv abs | high | 219 GAP cases under safety prompts; contracts do not deter attempts |
| fetch arxiv.org/abs/2603.20320 (Tool affordance) | 2026-11-12 | arXiv abs | high | Up to 85% violations; attempted vs executed |
| fetch arxiv.org/abs/2610.08082 (POLAR) | 2026-11-12 | arXiv abs | med | Reversibility pruning, mixed results |
| fetch arxiv.org/abs/2503.22738 (ShieldAgent) | 2026-11-12 | arXiv abs | med | +11.3%, recall 90.1% |
| MITRE ATLAS 2025 update AI agent techniques "AI Agent Tool Invocation" Zenity | 2026-11-12 | web search (vendors) | low | v5.x agent TTPs; counts conflict; primary not read |
| ISO/IEC 42001:2023 AI management system Annex A controls human oversight | 2026-11-12 | web search (secondary) | low | Standard is paywalled; control numbering conflicts |

## Citation spot-check (adversarial re-fetch of 10 load-bearing items)

| item | result | correction |
|---|---|---|
| AgentAbstain arXiv:2607.10059 | all numbers confirmed (263 pairs, 42 sandboxes, 17 models, paired acc 33.0-59.5%, post-hoc abstention 2.6% of n=115) | venue NOT confirmed: cite as arXiv preprint |
| Designing for Doubt arXiv:2606.02965 | confirmed incl. AIES 2026, 144 scenarios, compliance bias, 87.5-91% | term is 'runtime enforcement', not 'checkpoint wrapper'; v1 was ACM CAIS 2026 RLEval workshop |
| SteerBench-Work arXiv:2608.12654 | confirmed (106 scenarios, wrongly hold 28.1%, wrongly allow 1.0%) | preprint, no venue |
| Rabanser et al. arXiv:2602.16666 | confirmed (ICML 2026, 12 metrics, GAIA + tau-bench, 15 models) | - |
| SentryBench arXiv:2610.34535 | confirmed (840 episodes, refuse-more -> 100% over-refusal on 2/3 models, trust gate lowest harm) | preprint, no venue |
| CORA arXiv:2604.09155 | conformal execute/abstain confirmed | scope is risky actions generally, not irreversible-only; injection is 50/150 Harm tasks with no injection-specific results |
| GateArena (Jiang, Quinzan, Bhatt) | confirmed: NeurIPS 2026 workshop Agents in the Wild poster; 38%/48%/<1% withheld-tool attempts; 91/400 -> 0/400 | not on arXiv; no adversarial input; per-backbone mapping not stated |
| Mind the GAP arXiv:2602.16943 | 219 persisting cases confirmed | preprint |
| Railway blog + 2026-05-01 changelog | token, legacy volumeDelete, prod volume, recovery, 48h soft delete confirmed | Railway names neither PocketOS, Cursor nor any model |
| The Register 2026-04-27 | PocketOS, Cursor, Claude Opus 4.6 named; quote 'I guessed that deleting a staging volume via the API would be scoped to staging only.' | model/agent attribution rests on the founder's account as reported |

---

# Search log (Phase S, 2026-11-19)

Run by research sub-agents for the master agent. The dated query-by-query entries for incidents and standards are section (A) of `incidents_update_2026-11-19.md`; those for the literature are section (A) of `prior_art_update_2026-11-19.md`. Both files mark what could not be opened. Nothing in them has been re-verified by the master agent yet: a citation spot-check of the load-bearing items is planned before the pre-registration v3 freeze and again before submission.
