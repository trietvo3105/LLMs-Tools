from pathlib import Path
import sys
import json
import pandas as pd
import numpy as np
from faker import Faker
import gradio as gr

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
from base.base_class import BasePromptGenerator

system_message = """
You are a data analyst assistant. You are given a business problem and dataset requirements, then you have to analyze and output a structured JSON instruction for synthetic dataset generation. 

Follow this schema:
{
  "entities": [
    {
      "name": "<entity_name>",
      "columns": [
        {"name": "<column_name>", "type": "<data_type>", "role": "<primary_key/foreign_key/attribute>", "references": "<optional: entity.column>"}
      ],
      "count": <number_of_rows>
    }
  ],
  "formats": {
    "<entity_name>": "<csv/json>"
  },
  "dataset_type": "<tabular/plain_text>"
}

Output only the JSON.
"""
user_input = "I want a dataset of 5 customers and 10 orders. Each order should reference a customer. The customer dataset should have customer_id, name, and email. The order dataset should have order_id, customer_id, product, amount and review. I want both datasets as CSV files."
user_message = f"""
Business problem and requirements:
{user_input}
"""
prompt_generator = BasePromptGenerator("gpt-4o-mini")
system_prompt = {"role": "system", "content": system_message}
user_prompt = {"role": "user", "content": user_message}

SIMPLE_TYPES = {"int", "integer", "float", "decimal", "string"}
COMPLEX_ROLES = {"free_text", "description", "review", "comment"}

fake = Faker()


def generate_datasets(instruction_json):
    if not isinstance(instruction_json, dict):
        instruction_json = json.loads(instruction_json)
    dict_primary_keys_by_entity = dict()
    dict_generated_dataset = dict()
    for entity in instruction_json["entities"]:
        # Generate primary entities first
        if not any(c.get("role") == "foreign_key" for c in entity["columns"]):
            df, dict_primary_keys = generate_one_dataset(entity=entity)
            dict_primary_keys_by_entity[entity["name"]] = dict_primary_keys
            dict_generated_dataset[entity["name"]] = df

    for entity in instruction_json["entities"]:
        # Generate primary entities first
        if any(c.get("role") == "foreign_key" for c in entity["columns"]):
            df, dict_primary_keys = generate_one_dataset(
                entity=entity, dict_primary_keys_by_entity=dict_primary_keys_by_entity
            )
            dict_primary_keys_by_entity[entity["name"]] = dict_primary_keys
            dict_generated_dataset[entity["name"]] = df

    excel_file_paths = []
    print_dfs = []
    for name, df in dict_generated_dataset.items():
        excel_save_path = name + ".xlsx"
        df.to_excel(excel_save_path, index=False)
        excel_file_paths.append(excel_save_path)
        print_dfs.append(df.head(3).to_markdown(index=False))
    output_text = (
        f"{len(excel_file_paths)} Excel files are saved at {excel_file_paths} \n"
    )
    for excel_file_path, print_df in zip(excel_file_paths, print_dfs):
        output_text += f"### {excel_file_path}\n"
        output_text += f"{print_df}\n"
    return output_text


def generate_one_dataset(entity, dict_primary_keys_by_entity=None):
    rows = []
    name = entity["name"]
    n_rows = entity["count"]
    primary_keys = list(range(n_rows))
    primary_columns = [c for c in entity["columns"] if c.get("role") == "primary_key"]
    dict_primary_keys = {c["name"]: primary_keys for c in primary_columns}
    # each row : {'col1': value, 'col2': value}
    for i in range(n_rows):
        row = dict()
        for c in entity["columns"]:
            if c.get("role", "") == "foreign_key":
                ref = c.get("references")
                ref_name, ref_col = ref.split(".")
                value = np.random.choice(
                    dict_primary_keys_by_entity.get(ref_name).get(ref_col)
                )
            else:
                value = generate_value_one_column(column=c, row_idx=i)
            row[c["name"]] = value

        for c in entity["columns"]:
            if not is_simple_column(c) and row[c["name"]] is None:
                value = generate_complex_value(entity["name"], c, row)
                row[c["name"]] = value
        rows.append(row)
    df = pd.DataFrame(rows)
    return df, dict_primary_keys


def is_simple_column(column):
    if (column["type"] in SIMPLE_TYPES) and (column["name"] not in COMPLEX_ROLES):
        return True
    elif column["name"] in COMPLEX_ROLES:
        return False
    return False


def generate_value_one_column(column, row_idx: int):
    if is_simple_column(column):
        value = generate_simple_value(
            column, row_idx=row_idx, numeric_constraints=column.get("constraints")
        )
        return value
    else:
        value = None
    return value


def generate_simple_value(
    column, row_idx: int, numeric_constraints: None | list = None
):
    assert numeric_constraints is None or (
        isinstance(numeric_constraints, list) and len(numeric_constraints) == 2
    )
    name = column["name"].lower()
    type = column["type"]
    role = column.get("role")
    if type == "integer" or type == "int":
        if (role is not None) and (role.lower() == "primary_key"):
            value = row_idx
        else:
            value = (
                np.random.randint(1, 1000)
                if numeric_constraints is None
                else np.random.randint(numeric_constraints[0], numeric_constraints[1])
            )
    elif type == "float" or type == "decimal":
        value = (
            round(np.random.uniform(1.0, 1000.0), 2)
            if numeric_constraints is None
            else round(
                np.random.uniform(numeric_constraints[0], numeric_constraints[1]), 2
            )
        )
    elif type == "string":
        if name == "name":
            value = fake.name()
        elif name == "email":
            value = fake.email()
        elif name == "product":
            value = fake.word().title()
        else:
            value = None
    return value


def generate_complex_value(entity_name, column_info, row):
    messages = generate_message_for_complex_value(entity_name, column_info, row)
    response = prompt_generator.inference(prompt_generator.model_name, messages)
    return response


def generate_context_for_complex_value(row):
    context = ""
    for col_name, value in row.items():
        if (value is None) or ("id" in col_name):
            continue
        context += f"{col_name}: {value}\n"
    return context


def generate_message_for_complex_value(entity_name, column_info, row):
    system_message = "You are generating synthetic data for a tabular dataset."
    user_message = f"""    
    Entity: {entity_name}
    Field to generate: {column_info['name']}, type: {column_info['type']}

    Context:
    {generate_context_for_complex_value(row)}

    Instructions:
    - Generate a realistic and contextually appropriate value for the field "{column_info['name']}".
    - Make sure the value matches the expected type and style for this field.
    - Do not repeat the context or field name in the output.
    - Only output the value, nothing else.
    Now, generate the value.
    """
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]
    return messages


if __name__ == "__main__":

    def get_response(user_input):
        user_message = f"""
        Business problem and requirements:
        {user_input}
        """
        user_prompt = {"role": "user", "content": user_message}
        messages = [system_prompt, user_prompt]
        response = prompt_generator.inference(
            prompt_generator.model_name, messages, stream=True
        )
        text = ""
        for chunk in response:
            text += chunk.choices[0].delta.content or ""
            yield text

    with gr.Blocks() as ui:
        gr.Markdown("# Create Synthetic Dataset")
        with gr.Column():
            user_msg_input = gr.Textbox(
                label="User input",
                placeholder="Type your business problem and requirements here. Remember to include as many details as possible, e.g. the columns you want, the dataset(s) should be tubular dataset or text, and under CSV or JSON format, etc.",
            )
            gr.Markdown("## Generated instruction from 1st model:")
            llm1_instruction_output = gr.Markdown()
            gr.Markdown("## Dataset(s) generation result from 2nd model:")
            gr.Markdown(
                "### *please wait for some moment for the datasets to be generated*"
            )
            llm2_instruction_output = gr.Markdown()

            def do_entry(message):
                messages = [system_prompt, user_prompt]
                return message, messages

            user_msg_input.submit(
                fn=get_response,
                inputs=[user_msg_input],
                outputs=[llm1_instruction_output],
            ).then(
                fn=generate_datasets,
                inputs=[llm1_instruction_output],
                outputs=[llm2_instruction_output],
            )
    ui.launch(inbrowser=True)
