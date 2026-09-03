import { useState } from "react";
import { useNavigate } from "react-router-dom";

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

const LoanSimulator = () => {
  const [loanAmount, setLoanAmount] = useState("");
  const [loanDuration, setLoanDuration] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleCalculate = async (e) => {
    e.preventDefault();
    setError("");
    setResult(null);

    if (!loanAmount || !loanDuration) {
      setError("Please enter both loan amount and duration.");
      return;
    }
      
    try {
      const response = await fetch("/api/simulator/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          'X-CSRFToken': getCSRFToken(), // Include the CSRF token
        },
        body: JSON.stringify({
          loan_amount: parseFloat(loanAmount),
          loan_duration: parseInt(loanDuration, 10),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "An unexpected error occurred.");
      }

      const data = await response.json();
      setResult(data);

      // Save loan configuration locally
      localStorage.setItem("loan_configuration", JSON.stringify({
        amount: loanAmount,
        duration: loanDuration,
      }));
    } catch (err) {
      setError(err.message || " when fetching /api/simulator/");
    }
  };

  const handleProceedToLogin = () => {
    navigate("/login");
  };

  return (
    <div style={{ maxWidth: "600px", margin: "2rem auto", padding: "2rem" }} className="card">
      <h1>Loan Simulator</h1>
      <form onSubmit={handleCalculate} style={{ marginBottom: "1rem" }}>
        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="loanAmount">Loan Amount (€):</label>
          <input
            type="number"
            id="loanAmount"
            value={loanAmount}
            onChange={(e) => setLoanAmount(e.target.value)}
            placeholder="Enter loan amount"
            required
          />
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="loanDuration">Loan Duration (Months):</label>
          <input
            type="number"
            id="loanDuration"
            value={loanDuration}
            onChange={(e) => setLoanDuration(e.target.value)}
            placeholder="Enter loan duration"
            required
          />
        </div>
        <button type="submit">Calculate</button>
      </form>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {result && (
        <div style={{ marginTop: "1rem" }}>
          <h2>Loan Details</h2>
          <p>Interest Rate: {result.interest_rate}%</p>
          <p>Total Repayment: €{result.total_repayment}</p>
          <p>Monthly Installment: €{result.monthly_installment}</p>
          <button onClick={handleProceedToLogin} style={{ marginTop: "1rem" }}>
            Proceed to Login
          </button>
        </div>
      )}
    </div>
  );
};

export default LoanSimulator;
