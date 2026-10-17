// Mostra/esconde os dados pessoais conforme o tipo de reclamação
const radios = document.querySelectorAll('input[name="tipo"]');
const dados = document.getElementById('dados-pessoais');
const tituloMsg = document.getElementById('titulo-msg');
const nota = document.getElementById('nota-anonima');

function atualizar() {
  const identificada = document.querySelector('input[name="tipo"]:checked').value === 'identificada';
  dados.classList.toggle('escondido', !identificada);
  nota.style.display = identificada ? 'none' : 'block';
  tituloMsg.textContent = identificada ? '3. A sua reclamação' : '2. A sua reclamação';
}
radios.forEach(r => r.addEventListener('change', atualizar));
atualizar();

// Contador de letras
const msg = document.getElementById('mensagem');
const conta = document.getElementById('conta');
function contar() { conta.textContent = msg.value.length; }
msg.addEventListener('input', contar);
contar();
