describe("Chat Interaction", () => {
  it("should send a message and receive a response", () => {
    cy.visit("/chat");
    cy.get("input[placeholder='Type your message']").type("Hello!");
    cy.contains("Send").click();
    cy.contains("Hello! How can I assist you today?").should("be.visible");
  });
});