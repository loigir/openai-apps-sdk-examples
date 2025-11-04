import React from 'react';
import ReactDOM from 'react-dom/client';
import MonitoringDashboard from './dashboard';

// Entry point for the monitoring dashboard widget
const root = ReactDOM.createRoot(document.getElementById('allobye-monitoring-root'));
root.render(
  <React.StrictMode>
    <MonitoringDashboard />
  </React.StrictMode>
);
