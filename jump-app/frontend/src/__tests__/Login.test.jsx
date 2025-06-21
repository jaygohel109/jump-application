import { render, screen, fireEvent } from "@testing-library/react";
import App from "../App";

test("renders login screen", () => {
  render(<App />);
  const heading = screen.getByText(/Welcome to Jump Agent/i);
  expect(heading).toBeInTheDocument();

  const loginButton = screen.getByRole("button", { name: /Login with Google/i });
  expect(loginButton).toBeInTheDocument();
});

test("login button redirects to Google OAuth", () => {
  render(<App />);
  const loginButton = screen.getByRole("button", { name: /Login with Google/i });
  fireEvent.click(loginButton);
  expect(window.location.href).toContain("/auth/google/login");
});