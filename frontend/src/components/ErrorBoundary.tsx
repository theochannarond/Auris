import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    console.error("Erreur non gérée capturée :", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
          height: "100vh", textAlign: "center", padding: "24px"
        }}>
          <h2>Une erreur inattendue est survenue</h2>
          <p style={{ color: "#6B7280" }}>
            Veuillez rafraîchir la page. Si le problème persiste, contactez le support.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}