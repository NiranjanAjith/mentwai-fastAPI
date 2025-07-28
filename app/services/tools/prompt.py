from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from typing import Dict

from app.framework.tools import Tool

class PromptBuilderTool(Tool):
    name = "prompt_builder"
    description = "Tool to render prompts from Jinja templates"

    def __init__(self, template_dir: str = "app/prompts"):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.template_dir = template_dir

    def run():
        pass
    def confirm_setup(self):
        pass

    def render_from_file(self, template_path: str, variables: Dict= {}) -> str:
        """
        Render a prompt from a Jinja template file, given relative path and variables.
        """
        try:
            template = self.env.get_template(template_path)
            return template.render(**(variables or {}))
        except TemplateNotFound:
            raise ValueError(f"Template '{template_path}' not found in {self.template_dir}")

    def render_from_string(self, template_str: str, variables: Dict) -> str:
        """
        Render a prompt from a raw Jinja template string and variables.
        """
        template = self.env.from_string(template_str)
        return template.render(**variables)
    
    def __repr__(self):
        return f"<PromptBuilderTool dir={self.template_dir}>"


prompt_render = PromptBuilderTool()