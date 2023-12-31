from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.models import User
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from .models import BookRegister, BorrowingData
from django.contrib.auth import logout
from .forms import LoginForm, CadastroForm, EsqueciSenhaForm, NovaSenhaForm, RegistroLivrosForm, EmprestimoLivrosForm
from .utils import return_image, gerar_codigo, relatorio_estoque, graph_disponibility, graph_categories, graph_estado
from .GeradorPdf import GeradorPdf
from django.core.mail import EmailMessage
from django.contrib import messages
import io


def init(request):
    if request.method == 'GET':
        return render(request, 'static/inicial.html')

def register_auth(request):
    formregister = CadastroForm()
    form = LoginForm()

    if request.method == 'GET':
        return render(request, 'static/index.html', {'form': form, 'formregister': formregister})

    if(request.method == "POST"):
        formregister = CadastroForm(request.POST)
        if formregister.is_valid():
            email = formregister["email"].value()
            senha = formregister["senha_1"].value()
            if User.objects.filter(username=email).exists():
                return redirect('login_auth')
            
            usuario = User.objects.create_user(
                username=email,
                password=senha
            )
            usuario.save()
            return redirect('login_auth')
        else:
            return render(request, 'static/index.html', {'form': form,'formregister': formregister})
        
def login_auth(request):
    form = LoginForm()
    formregister = CadastroForm()

    if request.method == 'GET':
        return render(request, 'static/index.html', {'form': form, 'formregister': formregister})
        
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form['email'].value()
            senha = form['senha'].value()

            usuario = auth.authenticate(request, username=email, password=senha)
            if(usuario is not None):
                auth.login(request, usuario)
                return redirect('home')
        else:
            return render(request, 'static/index.html', {'form': form, 'formregister': formregister})
        
def esqueci_senha(request):
    form_esqueci_senha = EsqueciSenhaForm()
    if request.method == 'GET':
        return render(request, 'static/email.html', {'form_esqueci_senha': form_esqueci_senha})
    
    if request.method == 'POST':
        form_esqueci_senha = EsqueciSenhaForm(request.POST)
        
        if form_esqueci_senha.is_valid():
            request.session['email'] = form_esqueci_senha['email'].value()
            if request.session.get("email") is not None:
                request.session['codigo'] = gerar_codigo()
                emailstructure = EmailMessage('Código de Verificação', f'Seu código de segurança é: {request.session.get("codigo")}', to=[request.session.get("email")])
                emailstructure.send()
                return redirect('codigo_verify')              
        else:
            return render(request, 'static/email.html', {'form_esqueci_senha': form_esqueci_senha})
        
def codigo_verify(request):
    codigo = request.session.get('codigo')
    if request.method == 'GET':
        return render(request, 'static/codigoVerify.html')
    
    if request.method == 'POST':
        valores = []
        for i in range(1,7):
            valor = request.POST.get(f'num{i}') 
            valores.append(valor)
        code = ''.join(valores)

        if code == codigo:
            return redirect('trocar_senha')
        else:
            messages.error(request, "Digite um código válido!")
            return render(request, 'static/codigoVerify.html')
        
def trocar_senha(request):
    trocar_senha_form = NovaSenhaForm()
    email = request.session.get("email")
    if request.method == 'GET':
        return render(request, 'static/nova_senha.html', {'trocar_senha_form': trocar_senha_form})
    
    if request.method == 'POST':
        trocar_senha_form = NovaSenhaForm(request.POST)
        if trocar_senha_form.is_valid():
            user = User.objects.get(username=email)
            user.set_password(request.POST.get('senha'))
            user.save()
            return redirect('login_auth')
        else:
            return render(request, 'static/nova_senha.html', {'trocar_senha_form': trocar_senha_form})

@login_required(login_url='login_auth')
def home(request):
    formRegistroLivros = RegistroLivrosForm()
    formEmprestimoLivros = EmprestimoLivrosForm()
    if request.method == 'GET':
        books = BookRegister.objects.all()
        return render(request, 'static/home.html', {'books': books, 'formRegistroLivros': formRegistroLivros, 'formEmprestimoLivros': formEmprestimoLivros})
    else:
        return HttpResponse('Você precisa logar!')
    
@login_required(login_url='login_auth')
def pesquisa(request):
    if request.method == 'POST':
        nome_book = request.POST.get('nome_book')
        try:
            book = BookRegister.objects.get(nameBook=nome_book)
            return redirect('livroview', book_id=book.id)
        except BookRegister.DoesNotExist:
            return redirect('pesquisa_not_found/')
    else:
        return redirect('home')


@login_required(login_url='login_auth')
def registerbook(request):
    formRegistroLivros = RegistroLivrosForm()

    if request.method == 'POST':
        formRegistroLivros = RegistroLivrosForm(request.POST)
        if formRegistroLivros.is_valid():
            nome = formRegistroLivros['nameBook'].value()
            autor = formRegistroLivros['authorBook'].value()
            editora = formRegistroLivros['editoraBook'].value()
            estado = formRegistroLivros['estado'].value()
            descricao = formRegistroLivros['descrição'].value()
            categoria = formRegistroLivros['categoria'].value()
            disponivel = formRegistroLivros['disponivel'].value()
            image_content = return_image(nome)
    
            new_book = BookRegister(
                nameBook=nome,
                authorBook=autor,
                estado=estado,
                editoraBook=editora,
                descrição=descricao,
                image = image_content,
                categoria = categoria,
                disponivel = disponivel
            )
            new_book.save()
            return redirect('home')
        else:
            return redirect('home')
    else:
        return redirect('home')
    
@login_required(login_url='login_auth')    
def registerBorrowing(request):
    formEmprestimoLivros = EmprestimoLivrosForm()
    if request.method == 'POST':
        formEmprestimoLivros = EmprestimoLivrosForm(request.POST)
        if formEmprestimoLivros.is_valid():
            nome = formEmprestimoLivros['name'].value()
            email = formEmprestimoLivros['email'].value()
            book = formEmprestimoLivros['livro'].value()

            pdf = GeradorPdf('P','mm','A4')
            pdf.chapter_body(nome, book)
        
            new_borrowing = BorrowingData(
            name=nome,
            email=email,
            book=book,
            )

            new_borrowing.save()

            emailstructure = EmailMessage('Comprovante do Empréstimo', 'Envio do Comprovante PDF do seu empréstimo na Biblioteca Senai - Araguaína (TO)', to=[email])
            emailstructure.attach(f'Comprovante_emprestimo.pdf', pdf.output(dest='S'), 'application/pdf')
            emailstructure.send()
            return redirect('home')
        else:
            return redirect('home')
    else:
        return redirect('home')
    
@login_required(login_url='login_auth')    
def livroview(request, book_id):
    formRegistroLivros = RegistroLivrosForm()
    formEmprestimoLivros = EmprestimoLivrosForm()
    books = BookRegister.objects.all()
    book = BookRegister.objects.get(pk=book_id)
    return render(request, 'static/dados_livro.html', {'book': book, 'books': books, 'formRegistroLivros': formRegistroLivros, 'formEmprestimoLivros': formEmprestimoLivros})
    
@login_required(login_url='login_auth')
def deletebook(request, book_id):
    if request.method == 'POST':
        book = BookRegister.objects.get(pk=book_id)
        book.delete()
        return redirect('home')
    else:
        return render(request, 'static/home.html')

@login_required(login_url='login_auth')    
def updatebook(request, book_id):
    formEmprestimoLivros = EmprestimoLivrosForm()
    book = BookRegister.objects.get(pk=book_id)
    formRegistroLivros = RegistroLivrosForm(instance=book)
    if request.method == 'GET':
        return render(request, 'static/editar_livro.html', {'formRegistroLivros': formRegistroLivros, 'formEmprestimoLivros': formEmprestimoLivros, 'book': book})

    if request.method == "POST":
        formRegistroLivros = RegistroLivrosForm(request.POST, request.FILES, instance=book)
        formEmprestimoLivros = EmprestimoLivrosForm()
        if formRegistroLivros.is_valid():
            formRegistroLivros.save()
            return redirect('home')
        else:
            return render(request, 'static/editar_livro.html', {'formRegistroLivros': formRegistroLivros,'book': book, 'formEmprestimoLivros': formEmprestimoLivros})
    
@login_required(login_url='login_auth')
def historico(request):
    formRegistroLivros = RegistroLivrosForm()
    formEmprestimoLivros = EmprestimoLivrosForm()
    books = BookRegister.objects.all()
    emprestimos = BorrowingData.objects.all()
    if request.method == 'GET':
        return render(request, 'static/historico.html', {'books': books, 'emprestimos': emprestimos, 'formRegistroLivros': formRegistroLivros, 'formEmprestimoLivros': formEmprestimoLivros})

@login_required(login_url='login_auth')
def download_comprovante(request, emprestimo_id):
    emprestimo = BorrowingData.objects.get(pk=emprestimo_id)

    pdf_bytes = io.BytesIO()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Comprovante-{emprestimo.name}.pdf"'
    
    pdf_comprovante = GeradorPdf('P','mm','A4')
    pdf_comprovante.chapter_body(emprestimo.name, emprestimo.book)
    pdf_comprovante.output(pdf_bytes, dest='S')

    response.write(pdf_bytes.getvalue())

    return response

@login_required(login_url='login_auth')
def download_acervo(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Relatorio_acervo.pdf"'

    response.write(relatorio_estoque().getvalue())

    return response

@login_required(login_url='login_auth')
def download_categorias(request):
    formRegistroLivros = RegistroLivrosForm()
    formEmprestimoLivros = EmprestimoLivrosForm()
    if request.method == 'GET':
        fig_categoria = graph_categories()
        graph_html_categoria = fig_categoria.to_html(full_html=False)

        fig_disponibilidade = graph_disponibility()
        graph_html_disponibilidade = fig_disponibilidade.to_html(full_html=False)

        fig_estado = graph_estado()
        graph_html_estado = fig_estado.to_html(full_html=False)

        return render(request, 'static/grafico.html', {'graph_html_categoria': graph_html_categoria, 'graph_html_disponibilidade': graph_html_disponibilidade, 'graph_html_estado': graph_html_estado, 'formRegistroLivros': formRegistroLivros, 'formEmprestimoLivros': formEmprestimoLivros})


def logoutp(request):
    if request.user.is_authenticated:
        logout(request)
        return redirect('login_auth')
    
def handler404(request, exception):
    response = render(request, 'templates/404.html', context={})
    response.status_code = 404
    return response
