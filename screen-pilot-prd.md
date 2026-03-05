<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# [https://geminiliveagentchallenge.devpost.com/](https://geminiliveagentchallenge.devpost.com/) (so i am participating in this hackthon i have proivded you a thread the project i selected for making, you have the browse whole web and latest inforamtion avialable first breakdown the problem statement and rules and regaulations juding criteria then prepare in detail PRD define scope so i surely standout and major chance of winning hacktehon break down each task into smaller subtasks we will be using google sdk as they told to follow and react for frontend and fastapi for backend other you are free to chose whats best create me a day wise plan so i can complete it before deadline everything outline in the simplest language possible the deadline is 15 march everything i will need to complete this projec

one thing : it willl be very helpul if you find the github repo which have already done this or some code we can copy and modify in our project code available anywhere in web list all references and detailed PRD plan

You should build a focused UI Navigator agent called “ScreenPilot”: a browser copilot that looks at screenshots, understands the page, and fills a specific web form end‑to‑end using Gemini + Playwright, with a React frontend and FastAPI backend deployed on Google Cloud Run. Below is a breakdown of the hackathon requirements, a detailed PRD, architecture, day‑wise plan to finish before 15 March, and repos you can reuse.[^1][^2][^3]

***

## Hackathon track and problem

The Gemini Live Agent Challenge asks you to build next‑gen agents that go beyond simple text chat, using multimodal Gemini models plus Google Cloud. The UI Navigator track specifically wants agents that “become the user’s hands on screen”, visually understand screens (via screenshots/screen recordings) and perform real UI actions based on user intent.[^4][^3][^5]

Your chosen idea, ScreenPilot, fits this: it takes a user instruction like “Fill my weekly timesheet” or “Create a support ticket”, looks at the page screenshot, and then clicks, types and scrolls in the browser until the task is done. This shows exactly what the judges are looking for: visual understanding + executable actions + a live experience, not just Q\&A.[^6][^2][^1]

***

## Core rules and mandatory tech

Key “ALL projects MUST” requirements from Devpost and summaries:[^3][^4][^6]

- Use a Gemini model (e.g. gemini‑2.0‑flash / computer‑use model) for reasoning on screenshots and generating actions.[^2][^7]
- Use Google’s GenAI SDK **or** Agent Development Kit (ADK) as the way you call Gemini.[^7][^3]
- Use at least one Google Cloud service to host your agent (e.g. Cloud Run + optionally Firestore / Cloud Storage).[^4][^6][^3]

Other important constraints: submissions are online, open Feb 16 – mid‑March, and you must provide a public repo, deployment proof, and a demo video under 4 minutes. Your UI Navigator entry must clearly show it is driven by visual context (screenshots/screen recording), not just DOM selectors or APIs.[^8][^5][^6][^2][^4]

***

## Judging criteria (how to win)

Based on rules and community summaries, judging is roughly:[^6][^4]

- Innovation \& multimodal UX (~40%): Is the idea fresh and does it really use multimodal Gemini (vision + text, possibly computer‑use) in a meaningful way?
- Technical architecture (~30%): Clean architecture, good use of Gemini + SDK/ADK + Google Cloud, robustness and reasoning quality.[^2][^4]
- Demo \& presentation (~30%): Clear explanation of the problem, strong live demo that looks “live” and fluid, plus good README, diagram, and video.[^8][^4][^6]

For UI Navigator specifically, they explicitly ask whether the agent shows **visual precision** (understanding screen context) versus blind clicking, and whether the interaction feels “live” and context‑aware rather than slow turn‑based. So your demo must highlight: “Here is the screenshot, here is what Gemini understood, here is the exact element it chose and why.”[^4][^2]

***

## Product concept: ScreenPilot

ScreenPilot is a browser copilot that takes a simple natural‑language goal and completes a specific web workflow by seeing the screen and controlling it.[^9][^1]

Example demo flow: “Fill my weekly timesheet on this internal tool for this week, 8 hours per weekday.” → ScreenPilot opens the timesheet page in a controlled browser, takes screenshots, asks Gemini what to do next, and performs clicks/typing until all rows are filled.[^1][^2]

Instead of trying to automate the whole internet, you will support **one or two very tight flows** (e.g. a fixed demo timesheet app and/or a dummy support ticket form) so your demonstration is rock‑solid. This keeps scope realistic and lets you focus on visual accuracy, UX, and reliability, which judges care about.[^9][^1]

***

## PRD – in simple language

### Product goal

- Help people avoid boring, repetitive browser tasks like filling the same dashboard forms every day.[^1][^9]
- Let a user say what they want in plain language, and then watch the agent complete the online form automatically while explaining steps.[^6][^1]


### Primary users (for demo)

- Knowledge workers who repeatedly fill the same internal tools (timesheets, CRM tickets, helpdesk forms).[^1]
- For your hackathon demo, you only need a **single “persona”**: e.g. “SaaS support engineer who fills a weekly timesheet”.[^1]


### Main demo user story

- As a user, I open ScreenPilot, select a task like “Fill weekly timesheet”, give simple parameters (week dates + hours), then click Run.[^1]
- ScreenPilot opens the target web app in a browser, looks at screenshots, and automatically fills the correct fields, step by step, until the form is ready to submit.[^2][^1]

***

## Scope: what it will and will not do

### In‑scope (MVP)

- Support **1–2 predefined flows** that you fully control and can style for good visual clarity (e.g. a simple React timesheet app served from a static page or sub‑route).[^1]
- Use Gemini to understand screenshots and output a sequence of structured actions (JSON), such as click, type, scroll, mapped to real Playwright commands.[^2][^1]
- Show a simple React UI: choose task, provide parameters, start run, and see a live log of each step with short explanations.[^1]
- Use at least one Google Cloud service: deploy FastAPI + Playwright + Gemini logic to Cloud Run, and optionally log sessions to Firestore or Cloud Storage.[^4][^2]


### Out‑of‑scope (for hackathon version)

- Handling arbitrary websites or complex CAPTCHAs: restrict to your demo app or one stable third‑party site.[^9][^1]
- Multi‑user auth, teams, and role management: you can assume a single demo user/session.[^1]
- Perfect error handling: you handle the “happy path” plus a few common errors (e.g. invalid JSON from Gemini, element not found → retry once or stop gracefully).[^9][^1]

***

## Success criteria (what “good” looks like)

- For your chosen flow, ScreenPilot completes the task fully without manual clicks in most runs.[^1]
- Judges can clearly see that Gemini is reading the **visual UI** (screenshots) and not just using brittle DOM selectors; you can show overlays/coordinates or textual descriptions to prove this.[^10][^4][^2]
- Repo, architecture diagram, and demo video make the technical story obvious and professional.[^8][^6][^4]

***

## Tech stack and architecture

You want React for frontend and FastAPI for backend, plus Google’s SDK and Playwright.[^9][^1]

**Frontend (Web UI):**

- React + TypeScript (Vite or Create React App) for a small dashboard: task picker, parameter form, and real‑time log panel.[^11][^1]
- Simple components only: one page with a left panel (task \& controls) and right panel (logs + optional thumbnail screenshots).[^1]

**Backend (API + agent logic):**

- FastAPI (Python) as an HTTP API server, packaged in a Docker container.[^12]
- Gemini Python SDK (`google-genai` client) or official `google.genai` client to call a Gemini model (e.g. `gemini-2.0-flash` or a computer‑use model) using the Google GenAI SDK.[^13][^7][^2]
- Playwright (Python) to launch a Chromium browser, navigate to the target web app, take screenshots, and execute actions from Gemini.[^7][^2]

**Cloud and infra:**

- Google Cloud Run to host the FastAPI + Playwright container (counts as Google Cloud service and hosting).[^4][^2]
- Firestore or Cloud Storage to store logs and final screenshots; also helps show deeper Cloud usage in your submission.[^4][^1]
- Secret Manager or environment variables for `GEMINI_API_KEY` and any Cloud credentials.[^13][^2]

**Key SDKs / libraries (Python):**

- `google-genai` / `google-generativeai` or newer `google.genai` client for Gemini API.[^13][^2]
- `playwright` for browser automation.[^7][^2]
- `fastapi`, `uvicorn`, `pydantic` for API and data models.[^12]

***

## Agent behavior and data structures

### Action schema (JSON from Gemini)

Design a simple, explicit JSON schema that Gemini must follow, e.g.:[^2][^1]

```json
[
  {
    "action": "click",
    "target": {
      "type": "text_button",
      "text": "Add Entry"
    }
  },
  {
    "action": "type",
    "target": {
      "type": "field_label",
      "label": "Monday hours"
    },
    "value": "8"
  }
]
```

You’ll instruct Gemini to output only this JSON (no extra text) by using `response_mime_type="application/json"` and clear prompt instructions. FastAPI will parse this into Pydantic models and map each action to Playwright calls like `page.get_by_text("Add Entry").click()` or `page.get_by_label("Monday hours").fill("8")`.[^9][^2][^1]

### High‑level loop

- Take screenshot from Playwright and base64‑encode it.[^2][^1]
- Send `[text instruction, screenshot]` to Gemini with instructions to emit an array of actions in your schema.[^2][^1]
- Execute those actions via Playwright; after each “batch”, take another screenshot and repeat until task is complete or a stop condition is reached.[^2][^1]

This loop directly matches the official “computer use” pattern from Google’s docs, where the model sees a screenshot and suggests UI actions, repeated until completion.[^7][^2]

***

## Detailed feature list

**User‑facing features (MVP):**

- Task selection: dropdown with options like “Fill weekly timesheet”.[^1]
- Parameter input: simple text/number fields (e.g. week start date, hours per day).[^1]
- Run button: starts an API call to `/run-task` and shows streaming logs.[^1]
- Live log: each line shows step number, short description (“Gemini chose button ‘Add Entry’ and ScreenPilot clicked it”), and success/failure.[^1]
- Final status: success/failure summary, plus a thumbnail or link to final screenshot.[^9][^1]

**System features:**

- Backend endpoint `/api/run-task` that orchestrates the whole loop and streams progress (via server‑sent events, WebSocket, or polling).[^12][^1]
- Session storage: basic persistence of runs (task, parameters, start/end times, outcome) and optionally logs \& screenshots in Firestore/Cloud Storage.[^4][^1]
- Safety guardrail: before submitting forms or changing critical data, the agent pauses and asks the user to confirm via the UI.[^1]

***

## Day‑wise execution plan (from 5 March to 15 March)

Assuming today is 4 March night, here is a realistic schedule finishing core build by ~12–13 March and using last days for polish and submission.

### Day 1 (5 March) – Rules, scope, and environment

- Re‑read Devpost page: rules, UI Navigator description, submission checklist, judging criteria; take short notes in your own words.[^5][^6][^4]
- Finalize demo flow: pick **one primary flow** (e.g. demo timesheet app you control) plus maybe one backup if time allows.[^1]
- Create GCP project, enable Gemini API and Cloud Run, generate API key and set it locally (`GEMINI_API_KEY`).[^13][^2]


### Day 2 – Backend scaffolding and Gemini POC

- Initialize FastAPI project with a basic `/health` endpoint; run via `uvicorn` locally.[^12]
- Install Gemini and Playwright dependencies; run a **minimal Gemini text call** (no screenshots yet) from FastAPI to confirm credentials \& latency.[^13][^2]
- Set up `.env` handling and secrets loading; never hardcode keys.[^2]


### Day 3 – Playwright + screenshot POC

- Add Playwright to the FastAPI service; launch Chromium (headless = False first, for debugging).[^7][^2]
- Navigate to your demo timesheet page URL and capture a screenshot; verify locally in a `screenshots/` folder.[^9][^1]
- Build a small Python function `take_screenshot_and_call_gemini()` that sends screenshot + simple instruction (“Describe what you see in one sentence”) and logs Gemini’s description.[^2][^1]


### Day 4 – Design JSON schema and action executor

- Define the JSON schema for actions (Pydantic models) and write a function to execute one list of actions in Playwright (clicks, types, scrolls).[^9][^1]
- Write and iterate on the Gemini prompt so that it **always** returns valid JSON matching your schema; add a retry mechanism if JSON parsing fails once.[^2][^1]
- Hardcode a simple task (“Fill ‘Monday hours’ field with 8”) and verify the loop: screenshot → Gemini JSON → Playwright actions → screenshot.[^1]


### Day 5 – End‑to‑end task completion for one flow

- Expand prompt so Gemini can complete the entire timesheet in multiple steps using the loop; add a simple “goal reached?” condition (e.g. all rows filled).[^2][^1]
- Add basic logging structure: list of steps with action, Gemini reasoning summary, and success/failure.[^1]
- Confirm locally that a full run (with one button click plus several fills) completes in a reasonable time and is stable.[^9]


### Day 6 – React frontend skeleton

- Scaffold React + TypeScript app (Vite or CRA) with a single page layout.[^11]
- Build UI elements: task dropdown, parameter fields, Run button, and log panel; wire them to local mock data first.[^1]
- Integrate with FastAPI: call `/api/run-task` with fetch/Axios; start with simple “start + poll” pattern for run status.[^12]


### Day 7 – Live UX and screenshots

- Improve UX: show spinner/progress bar while agent runs and disable controls during execution.[^1]
- Implement streaming/polling of logs so the user sees each step in near real‑time (every 1–2 seconds is fine for “live” feel).[^6][^4]
- Add optional display of final screenshot (or small thumbnails at each major step) in the UI to emphasize visual understanding to judges.[^10][^1]


### Day 8 – Persistence and Cloud Run deployment

- Add minimal persistence: store each run (task, outcome, timestamps) in Firestore or store logs/screenshot paths in Cloud Storage.[^4][^2]
- Write a Dockerfile for FastAPI + Playwright (install Chromium as in official computer‑use docs) and test container locally.[^7][^2]
- Deploy to Cloud Run, configure environment variables, and ensure the React frontend can call the Cloud Run URL (fix CORS as needed).[^4][^2]


### Day 9 – Polish for judging criteria

- Improve prompts to stress **visual precision** (“do not guess; describe why you chose this element based on text/position; avoid random clicks”).[^4][^2]
- Add a simple confirmation dialog before final submission actions (e.g. clicking “Submit timesheet”) to demonstrate safety.[^1]
- Clean up logs so they are understandable to non‑technical judges: e.g. “Step 3: Gemini saw the label ‘Monday’ and filled 8 hours”.[^1]


### Day 10 – Documentation and architecture diagram

- Write a strong README: problem, solution, features, tech stack, architecture diagram, how to run locally, how to deploy, and where Gemini + Cloud are used.[^6][^4]
- Draw a simple architecture diagram (even in Excalidraw): User → React → FastAPI → Gemini API + Playwright → GCP (Cloud Run + Firestore/Storage).[^4][^1]
- Add comments in key files and ensure code structure is clean and easy to scan.


### Day 11 – Demo video and submission assets (13–14 March)

- Script a 3–4 minute demo: intro problem, show UI, run ScreenPilot end‑to‑end, show logs and final result, briefly show architecture diagram + Cloud Run console.[^8][^4]
- Record screen and voice‑over (even simple), upload as unlisted YouTube video, and link it in Devpost submission.[^6][^4]
- Double‑check Devpost form: description, links to repo, Cloud deployment proof screenshot/video, and ensure all required fields are completed before 15 March.[^4]

Use 15 March as buffer for bug‑fixing and final polish.

***

## Code you can reuse (GitHub and docs)

Here are repos and docs you can study and adapt (copy patterns, not blindly copy‑paste):

- **Gemini Web Navigator (Python, screenshots + browser control)** – `byt3bl33d3r/gemini-web-navigator` shows how to use Gemini’s vision capabilities and bounding boxes to control a browser from screenshots. It is close to what you’re building; you can adapt its screenshot loop and action mapping to your FastAPI setup.[^10]
- **WebSurferAI using Gemini + Playwright** – `kvcops/WebSurferAI-Using-Gemini` is an autonomous web assistant that uses Gemini Pro Vision with Playwright to navigate, click, fill forms, and extract information. Its structure for tasks, logging, and error recovery is a good reference.[^9]
- **Official Gemini “Computer Use” docs** – `Computer Use | Gemini API` shows how to use Gemini to take screenshots and emit UI actions, with Playwright integration and code snippets for looping screenshots and actions.[^2] This is exactly aligned with the UI Navigator track.
- **ADK Computer Use Toolset** – The ADK’s computer‑use toolset explains how to attach a `ComputerUseToolset` with Playwright, similar to what you’re writing manually. Use it as inspiration or, if time permits, as an alternative implementation.[^7]
- **Google Gemini API Cookbook** – The `google-gemini/cookbook` repo includes many small examples on prompts, tools, and multimodal usage that are useful for shaping your prompts and JSON outputs.[^13]
- **BrowserUse examples (with Gemini)** – Articles and examples integrating `browser-use` with Gemini show patterns for writing natural‑language tasks that translate into Playwright actions; even if they use other LLMs, the pattern is helpful.[^14]
- **FastAPI + Playwright web agent tutorial** – A tutorial on building an autonomous web browsing agent with Python, FastAPI, Playwright, and an LLM shows how to structure routes and long‑running browser tasks.[^12]
- **Gemini Live Agent starter for React + Live API** – `TechAsad/gemeni-live-agent` is a React‑based starter for the Live API; while it targets audio, you can copy patterns for websocket streaming and UI layout if you later add voice.[^15]

These references plus the plan in your attached PDF (which already covers UI Navigator rationale, basic PRD, SDK usage, and step‑by‑step build) give you end‑to‑end guidance.[^1]

***

## Submission assets you must prepare

To maximize your score, prepare these clearly:[^6][^4]

- **Devpost description:** Problem (manual browser tasks), your solution (ScreenPilot UI Navigator), target users, tech stack, and what’s unique (visual precision, safety, logs).
- **Public GitHub repo:** Clean structure (`frontend/`, `backend/`), README, env instructions, architecture diagram, and minimal setup steps.
- **Deployment proof:** Screenshot or short video of Cloud Run service + Firestore/Storage usage, and mention this explicitly on Devpost.[^4]
- **Demo video (<4 minutes):** Strong narration, smooth run, show both UI and a peek at Gemini logs/Cloud dashboard.[^8][^4]

If you follow this PRD, stick to one very polished flow, and keep the UX simple and clear, you’ll strongly match the UI Navigator track and judging criteria and give yourself a serious chance to stand out.
<span style="display:none">[^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26]</span>

<div align="center">⁂</div>

[^1]: so-give-me-indetail-guide-which-one-of-three-would.pdf

[^2]: https://ai.google.dev/gemini-api/docs/computer-use

[^3]: https://www.startupnetworks.co.uk/links/link/29508-gemini-live-agent-challenge/

[^4]: https://geminiliveagentchallenge.devpost.com/rules

[^5]: https://geminiliveagentchallenge.devpost.com/updates

[^6]: https://www.reddit.com/r/ambitionarena7/comments/1r7yliv/gemini_live_agent_challenge/

[^7]: https://google.github.io/adk-docs/tools/gemini-api/computer-use/

[^8]: https://www.youtube.com/watch?v=-AAwoj4qN8M

[^9]: https://github.com/kvcops/WebSurferAI-Using-Gemini

[^10]: https://github.com/byt3bl33d3r/gemini-web-navigator

[^11]: https://www.youtube.com/watch?v=HakXg-hFZ_c

[^12]: https://www.linkedin.com/pulse/how-build-autonomous-web-browsing-agent-pablo-schaffner-bofill-emdre

[^13]: https://github.com/google-gemini/cookbook

[^14]: https://anhtester.com/blog/ai-in-test-automation-browser-use-web-ui-part-3-write-tasks-in-code-b676.html

[^15]: https://github.com/TechAsad/gemeni-live-agent

[^16]: https://www.linkedin.com/posts/yassine-ben-acha_ai-machinelearning-nlp-activity-7431572259540156416-lQcl

[^17]: https://www.youtube.com/shorts/mvpvKg8QQ9c

[^18]: https://dev.to/ibtisamafzal/how-we-built-voyance-an-ai-agent-that-researches-the-web-by-seeing-it-214h

[^19]: https://github.com/masalachai/gemini-git-browser

[^20]: https://www.linkedin.com/posts/ayoadedeji_gemini-live-agent-challenge-activity-7430601548201807872-qSqY

[^21]: https://www.reddit.com/r/vibecoding/comments/1p4in9f/the_unspoken_hero_of_antigravity_browser/

[^22]: https://www.linkedin.com/posts/johnbkane3_geminiliveagentchallenge-buildinpublic-ai-activity-7432904716121976832-3U-d

[^23]: https://dev.to/kamaumbuguadev/i-built-an-ai-that-sees-your-screen-and-speaks-your-answers-heres-how-5dhl

[^24]: https://developer.android.com/studio/gemini/agent-files

[^25]: https://www.linkedin.com/posts/gogu-arjun_ai-webautomation-python-activity-7320451210224746496-ARpf

[^26]: https://ai.google.dev/gemini-api/docs/tools

