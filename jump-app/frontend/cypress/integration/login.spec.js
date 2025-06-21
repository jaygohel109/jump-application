describe("Login Flow", () => {
  it("should redirect to Google OAuth on login", () => {
    cy.visit("/");
    cy.contains("Login with Google").click();
    cy.url().should("include", "/auth/google/login");
  });
});