```
██╗   ██╗ ██████╗  ██████╗ ██████╗ █████╗
██║   ██║██╔═══██╗██╔════╝██╔════╝██╔══██╗
██║   ██║██║   ██║██║     ██║     ███████║
╚██╗ ██╔╝██║   ██║██║     ██║     ██╔══██║
 ╚████╔╝ ╚██████╔╝╚██████╗╚██████╗██║  ██║
  ╚═══╝   ╚═════╝  ╚═════╝ ╚═════╝╚═╝  ╚═╝
```

# Vocca AI Tech Test

## Objectives

Your goal is to start from this [LiveKit Agents](https://docs.livekit.io/agents/) codebase and build a medical assistant able to book appointments.
You are free to use any other tools, patterns or library you might need to achieve this mission.

### Objective 1: Build a basic booking flow
The assistant should be able to complete the booking workflow following these steps:

1. Greet the patient on arrival
2. Collect the patient's identity
   - First name
   - Last name
   - Birthdate
3. Determine the patient's visit motive among a provided list
4. Find suitable availabilities for a given motive, for the patient
5. Book the appointment with all the collected information on a calendar app of your choice

#### About external services

You will need to call an external service either for availabilities retrieval and/or calendar slot booking.

- **Availabilities**: Should come from your own API (Flask/FastAPI server) with predefined availability slots. Do not use external authenticated services for this. We strongly recommend to vibecode it to save some time.
- **Calendar booking**: Should only log the booking action and arguments (no actual external calendar integration required)

### Objective 2: Focus on Name Collection

Name collection is a critical part of the booking process and you should pay special attention to spelling accuracy:

**Common spelling problems you should observe and solve:**

- Similar sounding names: "Chauveau" vs "Chaubot", "Mahaut" vs "Mao"
- Double letters: "Anne", "Philippe"
- Special characters (accents, space, hyphen): "Jean-Philippe", "Gaël", "N'Djoli", "De la Barrère"
- Silent letters: "Renault", "Lefèbvre"
- Names including common words: "Pierre Rochet" might be transcribed as "Pierre Rocher"
- Names with a foreign origin: "N'Jamen N'Jantcho", "Nguyen", "D'Haene", "Pham", "Xu", "Tchatchouang"

### BONUS: How would you ensure quality of your voice bot in the long run?

On a side markdown file, describe how you would ensure quality of your voice bot in the long run.

- How would you ensure long-term voice bot quality?
- How would you introduce new features?
- How would you avoid/monitor possible regressions?
- How would you test & choose different models or configuration?

## Quick Start

### Installation

```shell
uv sync
uv pip install -r pyproject.toml
cp .env.example .env
```

### API Keys

**LiveKit keys**

1. Create an account on [LiveKit Cloud](https://cloud.livekit.io)
2. Under [Settings > Project Settings](https://cloud.livekit.io/projects/p_5rzkc7cwlno/settings/project), collect the project URL and copy paste it to `LIVEKIT_URL` (using wss:// protocol)
3. Under [Settings > API Keys](https://cloud.livekit.io/projects/p_5rzkc7cwlno/settings/keys) generate a new pair of key/secret and add it to your `.env` file

**Azure keys**
We will provide those keys for you, in a secure way.

### Run the project

```shell
uv run main.py dev
```

Then go to [LiveKit Agents Playground](https://agents-playground.livekit.io).
Your agent should connect to the playground room and start talking.
