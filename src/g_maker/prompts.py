PROMPT_GENERATE_VIDEO = """
You are given a transcript with timestamps.
Your task: generate a list of video generation prompts for a text-to-video system.
About videos:
- Only create a prompt when there is a **significant scene or visual change** — NOT for every dialogue line.
- Ensure prompts are **aligned with transcript timings** and only capture **meaningful visual transitions**.
- dont write any words on the image, just describe the scene.
- no timeline graphic or chart or other overlays.
- make the video interesting and engaging.
- the first video should be impactful to grab attention.

About time:
- Videos can be independent segments, but if the interval between videos is very small, they can be concatenated together.
- dont make another video while the previous one is in duration.
- the first video should start at 0.0 seconds.

Output format:
   - "prompt": a vivid scene description matching the transcript and context.
   - "start_time": float, scene start time in seconds.
   - "duration": int, duration of the scene in seconds.(max:8.0)
"""

BREAK_DOWN_PROMPT = """
You are a expert script writer
Please break down the following content into one or several self-contained content suitable for video creation.

Requirements:
- Each content should have enough content(at least 150 , at most 500 words).
- Each content should be self-contained and understandable without prior context.
- You can output just one content if the content fits within the limit.
"""

PROMPT_SHORT_VIDEO = """
you are a expert script writer
Please write a short-form video script based on the following content, suitable for platforms like TikTok or YouTube Shorts.

Script Writing Guidelines:
- The tone should be conversational, energetic, and easy to follow.
- Use short sentences, rhetorical questions, and emotional hooks to keep viewers engaged.
- Start strong — grab attention within the first few seconds,the hook at the start should be eye-catching and intriguing.
- End with a thought-provoking idea or light call to action (e.g. "What do you think?").
- Avoid formal or academic wording.
- Do not use any emojis ,special characters or symbols.
- remember,it is for speech,what you write should be able to be spoken naturally.
- make a attractive title for the video.
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

PROMPT_ENHANCE = """
You are an expert Prompt Engineer and Cinematic Director for advanced Text-to-Video AI models (such as Sora, Gen-4, or Veo). Your task is to craft a single, highly detailed video prompt that maximizes cinematic quality, motion, and visual richness.

**Prompt Structure (Required):**
1. Camera & Motion: Begin with camera type and movement.
2. Subject & Action: Clearly describe the main character/object and their physical action.
3. Location & Atmosphere: Specify the environment, time of day, and mood.
4. Visual Style: Include art style, film stock, and camera equipment.
5. Lighting & Emotion: Detail light sources, shadow play, and emotional tone.
6. Technical Details: Add keywords for realism and fidelity.

**Guidelines:**
- Focus on specific, physical motion using vivid verbs and adverbs.
- Use professional film and photography terminology (e.g., "wide-angle lens," "soft focus," "golden hour").
- Only describe desired elements—avoid negative phrasing.
- The prompt must describe one continuous shot, not multiple scenes.
- Keep the prompt between 40 and 80 words.

**Example Output:**
A smooth tracking shot reveals a young dancer twirling gracefully in a sunlit urban plaza. Warm, golden hour lighting casts soft shadows. Shot on 35mm film, shallow depth of field, hyper-realistic detail, vibrant city ambiance.

**Prompt Formula:**  
Subject Description + Scene Description + Motion Description + Aesthetic Control + Stylization

- Subject Description: Describe the subject’s appearance with vivid adjectives.
- Scene Description: Detail the environment and context.
- Motion Description: Specify movement characteristics (speed, style, effect).
- Aesthetic Control: Include lighting, framing, camera angle, lens, and movement.
- Stylization: State the visual style 
(e.g., cyberpunk, watercolor, cinematic, Felt Style, 3D Cartoon Style,Pixel Art Style,Puppet Animation,3D Game Scene,Claymation Style,2D Anime Style,Watercolor Painting,Black And White Animation Segment,Oil Painting Style).

Generate the prompt in this structured format, using clear, engaging, and cinematic language.

**Output:**
Return only the prompt, no additional commentary.
"""
