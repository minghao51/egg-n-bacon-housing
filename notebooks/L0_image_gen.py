# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.0
#   kernelspec:
#     display_name: py311cv
#     language: python
#     name: python3
# ---

# %%
from diffusers import DiffusionPipeline

pipe = DiffusionPipeline.from_pretrained("SG161222/Realistic_Vision_V6.0_B1_noVAE")

prompt = "Astronaut in a jungle, cold color palette, muted colors, detailed, 8k"
image = pipe(prompt).images[0]

# %%
from diffusers import StableDiffusionPipeline
from diffusers.models import AutoencoderKL

model = "stabilityai/your-stable-diffusion-model"
vae = AutoencoderKL.from_pretrained("stabilityai/sdxl-vae")
pipe = StableDiffusionPipeline.from_pretrained(model, vae=vae)


# %%
import torch
from diffusers import DiffusionPipeline

pipeline = DiffusionPipeline.from_pretrained("stable-diffusion-v1-5/stable-diffusion-v1-5", torch_dtype=torch.float16)
# pipeline.to("cuda")a
pipeline("An image of a squirrel in Picasso style").images[0]
