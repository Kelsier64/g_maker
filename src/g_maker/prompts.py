PROMPT_GENERATE_VIDEO = """
You are given a transcript with timestamps.
Your task: generate a list of video generation prompts for a text-to-video system.
Rules:
1. Only create a prompt when there is a **significant scene or visual change** — NOT for every dialogue line.
2. Ensure prompts are **aligned with transcript timings** and only capture **meaningful visual transitions**.
3. Videos can be independent segments, but if the interval between videos is very small, they can be concatenated together.
4. dont make another video while the previous one is in duration.
5. dont write any words on the image, just describe the scene.
6. the video generation model is poor ,so keep the prompts simple and focused.
7. no timeline graphic or chart or other overlays.
Output format:
   - "prompt": a vivid scene description matching the transcript and context.
   - "start_time": float, scene start time in seconds.
   - "duration": integer, duration of the scene in seconds.(max:15)
"""

PROMPT_SHORT_VIDEO = """
you are a expert script writer
Please break down the following content into one or several short-form video scripts suitable for platforms like TikTok or YouTube Shorts.

Requirements:
- Each script should be less than 180 seconds in total.
- Each script should be self-contained and understandable without prior context.
- Each script should have enough content.
- You can output just one script if the content fits within the 180-second limit.
- Each output should be a dictionary with the following keys:
  - 'title': A short, catchy video title.
  - 'script': The full narration for the video, written in a natural, spoken tone.

Script Writing Guidelines:
- The tone should be conversational, energetic, and easy to follow.
- Use short sentences, rhetorical questions, and emotional hooks to keep viewers engaged.
- Start strong — grab attention within the first few seconds,the hook at the start should be eye-catching and intriguing.
- End with a thought-provoking idea or light call to action (e.g. "What do you think?" or "Share this with a friend").
- Avoid formal or academic wording.
"""

PROMPT_CONTENT_CLEAN = """
You are a video script cleaning assistant. Your task is to refine a transcript by preserving the main content while removing unnecessary parts. Please do the following:
- translate to english.
- Remove introductory and closing greetings, such as "Hi everyone" or "Thanks for watching."
- Remove channel promotions, like "Remember to like and subscribe."
- Remove unrelated small talk or off-topic banter.
- Keep the original wording and tone as much as possible, with minor edits for clarity.
- Output a cleaned and concise version of the script that still feels authentic and natural.
Return only the cleaned script, no additional commentary.
"""