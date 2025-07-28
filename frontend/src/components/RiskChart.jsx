// src/components/RiskChart.jsx
import { useEffect, useState } from 'react';
import axios from 'axios';
import { Bar } from 'react-chartjs-2';

const RiskChart = () => {
  const [riskData, setRiskData] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:5000/api/analyze')
      .then(res => setRiskData(res.data.scores))
      .catch(console.error);
  }, []);

  const data = {
    labels: riskData.map((d, i) => `Zone ${i+1}`),
    datasets: [{
      label: 'Risk Score',
      data: riskData,
      backgroundColor: 'rgba(255, 99, 132, 0.6)',
    }],
  };

  return <Bar data={data} />;
};

export default RiskChart;
