import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import LoginPage from "./LoginPage";

describe("LoginPage", () => {
  it("affiche le titre Auris", () => {
    render(<LoginPage />);
    expect(screen.getByText("Auris")).toBeInTheDocument();
  });

  it("affiche le bouton de connexion", () => {
    render(<LoginPage />);
    expect(screen.getByText("Se connecter")).toBeInTheDocument();
  });
});
