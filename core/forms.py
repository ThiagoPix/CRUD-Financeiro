from django import forms


def adicionar_erros(form, erro):
    """Leva os erros de uma ValidationError das regras (servicos.py) para os campos do formulário."""
    if hasattr(erro, "error_dict"):
        for campo, mensagens in erro.message_dict.items():
            form.add_error(campo if campo in form.fields else None, mensagens)
    else:
        form.add_error(None, erro.messages)


class CadastroForm(forms.Form):
    organizacao = forms.CharField(label="Nome da organização", max_length=120)
    usuario = forms.CharField(label="Usuário", max_length=150, help_text="Letras, números e @/./+/-/_ apenas.")
    senha = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    confirmar_senha = forms.CharField(label="Confirmar senha", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def clean(self):
        dados = super().clean()
        if dados.get("senha") and dados.get("confirmar_senha") and dados["senha"] != dados["confirmar_senha"]:
            self.add_error("confirmar_senha", "As senhas não conferem.")
        return dados
