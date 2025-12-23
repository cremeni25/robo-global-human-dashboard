<script type="text/babel">
const Section = ({ title, children }) => (
  <div style={{ border: "1px solid #ddd", borderRadius: "12px", padding: "16px", marginBottom: "16px" }}>
    <h2>{title}</h2>
    {children}
  </div>
);

function App() {
  return (
    <div style={{ maxWidth: "800px", margin: "40px auto", fontFamily: "Arial" }}>
      <Section title="Estado Atual do Sistema">
        <p><strong>Estado:</strong> Operando com estabilidade controlada</p>
        <p><strong>Modo:</strong> Observação</p>
        <p><strong>Última decisão:</strong> Validada institucionalmente</p>
      </Section>

      <Section title="Decisões em Curso">
        <p>Expandir exposição do Produto A</p>
        <p>Risco percebido: Moderado</p>
      </Section>

      <Section title="Mensagem do Sistema ao Humano">
        <em>Nenhuma ação humana é necessária neste momento.</em>
      </Section>
    </div>
  );
}

ReactDOM.render(<App />, document.getElementById("root"));
</script>
