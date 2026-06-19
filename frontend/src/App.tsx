import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import AdminConsole from "./pages/AdminConsole";
import DataQualityDashboard from "./pages/DataQualityDashboard";
import StewardshipQueue from "./pages/StewardshipQueue";
import GoldenRecordExplorer from "./pages/GoldenRecordExplorer";
import ComplianceChat from "./pages/ComplianceChat";
import LineageVisualizer from "./pages/LineageVisualizer";
import CustomerPortal from "./pages/CustomerPortal";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-900">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<AdminConsole />} />
            <Route path="/data-quality" element={<DataQualityDashboard />} />
            <Route path="/stewardship" element={<StewardshipQueue />} />
            <Route path="/golden-records" element={<GoldenRecordExplorer />} />
            <Route path="/compliance-chat" element={<ComplianceChat />} />
            <Route path="/lineage" element={<LineageVisualizer />} />
            <Route path="/customer-portal" element={<CustomerPortal />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
