const Section = ({ title, children }) => (
  <div style={{
    border: "1px solid #ddd",
    borderRadius: "12px",
    padding: "16px",
    marginBottom: "16px",
    background: "#ffffff"
  }}>
    <h2>{title}</h2>
    {children}
  </div>
);

function App() {
  return (
    <div style={{
      maxWidth: "900px",
      margin: "40px auto",
      fontFamily: "Arial, sans-serif"
    }}>
      <Section title="Estado Atual do Sistema">
        <p><strong>Estado:</strong> Operando com estabilidade controlada</p>
        <p><strong>Modo:</strong> Observação</p>
        <p><strong>Última decisão:</strong> Validada institucionalmente</p>
      </Section>

      <Section title="Decisões em Curso">
        <p><strong>Decisão:</strong> Expandir exposição do Produto A</p>
        <p><strong>Risco percebido:</strong> Moderado</p>
        <p><strong>Status:</strong> Em observação ativa</p>
      </Section>

      <Section title="Mensagem do Sistema ao Humano">
        <em>
          Neste momento, continuar observando é mais seguro do que acelerar.
          Nenhuma ação humana é necessária.
        </em>
      </Section>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
