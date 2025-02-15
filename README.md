# LLM Tools

This is a repository with different tools that use LLM to perform tasks like website summarizing, cover letter writing (from the resume and job description), etc.

## Important note
Pretty much all of the tools use APIs to call models from OpenAI or Anthropic. If the API call is for a closed-source model, the user must have an API key and some credit in his/her account.

<u>Example:</u> for OpenAI API, one should go to https://platform.openai.com/ to top up some amount into her account and set up an API key.

However, there will be some tools using free, local, open-source models like Llama3.2, in that case, model using won't cost any credit.

## Setup
Currently, using anaconda to set up the environment is recommended. To do so, run:
```
conda env create -f environment.yml
```

Then before using each tool, please activate the environment by:
```
conda activate llms
```

As mentioned above, API key is required to run the tools, so one must create a .env in the root directory. **The filename must be exactly .env**. Then copy the API key into it.

For examle: for OpenAI API key, create this line in .env file:
```
OPENAI_API_KEY=API_KEY_goes_here
```

## 1. Website summarizer
```
Usage: python web_summarize.py website_url_goes_here
```
As its name, this tool will analyze and summarize the content of a (public) website using **GPT-4o-mini** model. Using GPT-4o-mini means that the tool requires you to have a positive credit in the OpenAI API account, but it will charge you a very very small amount of your credit for every time the tool is called.

The result should be somehthing like this:
![web_summarize_result](./images/web_summarizer_result.jpeg)