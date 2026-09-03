import { useState, useEffect } from "react";

// Function to get the CSRF token from cookies
function getCSRFToken() {
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'csrftoken') {
      return value;
    }
  }
  return null;
}

const LoanApplication = () => {
  const [loanConfiguration, setLoanConfiguration] = useState(null);
  const [monthlyIncome, setMonthlyIncome] = useState("");
  const [monthlyExpenses, setMonthlyExpenses] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Load loan configuration from localStorage
  useEffect(() => {
    const storedConfig = localStorage.getItem("loan_configuration");
    if (storedConfig) {
      setLoanConfiguration(JSON.parse(storedConfig));
    }
  }, []);

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setResult(null);
    setIsLoading(true); // Show loading state

    // Simple validation
    if (!monthlyIncome || !monthlyExpenses) {
      setError("Please fill in all required fields.");
      setIsLoading(false); // Stop loading state
      return;
    }

    try {
      const response = await fetch("/api/applications/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(), // Include CSRF token
        },
        body: JSON.stringify({
          monthly_income: parseFloat(monthlyIncome),
          monthly_expenses: parseFloat(monthlyExpenses),
          amount: loanConfiguration.amount,
          duration: loanConfiguration.duration,
        }),
      });

      if (!response.ok) {
        const errorData = await response.text();
        throw new Error(errorData || "An unexpected error occurred.");
      }

      // Process JSON response
      const data = await response.json();
      setResult(data);

      // Show the result based on the application status
      if (data.application_status === "accept") {
        alert("Loan application approved!");
      } else if (data.application_status === "interview") {
        alert("Loan requires further review.");
      } else if (data.application_status === "reject") {
        alert("Loan application rejected.");
      }
    } catch (err) {
      setError(err.message || "Error during application submission.");
    } finally {
      setIsLoading(false); // End loading state
    }
  };

  return (
    <div style={{ maxWidth: "600px", margin: "0 auto", padding: "2rem" }}>
      <h1>Loan Application</h1>
      {loanConfiguration ? (
        <div>
          <h2>Loan Details</h2>
          <p>Loan Amount: {loanConfiguration.amount}€</p>
          <p>Loan Duration: {loanConfiguration.duration} months</p>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: "1rem" }}>
              <label htmlFor="monthlyIncome">Monthly Income (€):</label>
              <input
                type="number"
                id="monthlyIncome"
                value={monthlyIncome}
                onChange={(e) => setMonthlyIncome(e.target.value)}
                required
              />
            </div>
            <div style={{ marginBottom: "1rem" }}>
              <label htmlFor="monthlyExpenses">Monthly Expenses (€):</label>
              <input
                type="number"
                id="monthlyExpenses"
                value={monthlyExpenses}
                onChange={(e) => setMonthlyExpenses(e.target.value)}
                required
              />
            </div>
            <button type="submit" disabled={isLoading}>
              Submit Application
            </button>
          </form>

          {isLoading && <p>Loading...</p>} {/* Indicates loading state */}
          {error && <p style={{ color: "red" }}>{error}</p>}
          {result !== null && (
            <div>
              <h3>Application Result</h3>
              <p>Credit Score: {result.credit_score}</p>
              <p>Status: {result.application_status}</p>
            </div>
          )}
        </div>
      ) : (
        <p>Loading loan details...</p>
      )}
    </div>
  );
};

export default LoanApplication;
