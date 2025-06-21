import { render, screen } from "@testing-library/react";
import ChatUI from "../ChatUI";

test("renders chat interface", () => {
  render(<ChatUI />);
  const inputBox = screen.getByPlaceholderText(/Type your message/i);
  expect(inputBox).toBeInTheDocument();

  const sendButton = screen.getByRole("button", { name: /Send/i });
  expect(sendButton).toBeInTheDocument();
});