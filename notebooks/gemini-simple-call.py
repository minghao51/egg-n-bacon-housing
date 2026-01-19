# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.0
#   kernelspec:
#     display_name: demo
#     language: python
#     name: python3
# ---

# %%
# testing gemini api call with image and text

# %%
import os

from langchain_core.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAI

os.environ['GOOGLE_API_KEY'] = ''

class LLM:

    llm_source = {'google': GoogleGenerativeAI}

    def __init__(self,
                 model_name,
                 llm_provider
                 ):
        self.model_name = model_name #'gemini-1.5.flash'
        self.llm_provider = llm_provider #'google'
        self.llm = self.create_llm()


    def get_prompt_template(self, prompt_name):
        prompt_templates = {'hello':'hello {name}!'}
        prompt_template = PromptTemplate.from_template(prompt_templates[prompt_name])

        return prompt_template

    def create_llm(self):
        llm =  self.llm_source[self.llm_provider](model = self.model_name)

        return llm


    def invoke(self, prompt_name, **prompt_kwargs):

        prompt_template = self.get_prompt_template(prompt_name)
        chain = prompt_template | self.llm
        response = chain.invoke(input = prompt_kwargs['prompt_kwargs'])

        return response

if __name__ == '__main__':

    llm = LLM(model_name = 'gemini-1.5-flash',
              llm_provider='google'
                )

    response = llm.invoke(prompt_name='hello', prompt_kwargs={'name':'Edwin'})
    print (response)




# %%
