import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Sidebar } from "./components/Sidebar";
import AdminConsole from "./pages/AdminConsole";
import DataQualityDashboard from "./pages/DataQualityDashboard";
import StewardshipQueue from "./pages/StewardshipQueue";
import GoldenRecordExplorer from "./pages/GoldenRecordExplorer";
import ComplianceChat from "./pages/ComplianceChat";
import LineageVisualizer from "./pages/LineageVisualizer";
import CustomerPortal from "./pages/CustomerPortal";

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className="h-full"
      >
        <Routes location={location}>
          <Route path="/" element={<AdminConsole />} />
          <Route path="/data-quality" element={<DataQualityDashboard />} />
          <Route path="/stewardship" element={<StewardshipQueue />} />
          <Route path="/golden-records" element={<GoldenRecordExplorer />} />
          <Route path="/compliance-chat" element={<ComplianceChat />} />
          <Route path="/lineage" element={<LineageVisualizer />} />
          <Route path="/customer-portal" element={<CustomerPortal />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-900">
        <Sidebar />
        <main className="flex-1 overflow-hidden">
          <AnimatedRoutes />
        </main>
      </div>
    </BrowserRouter>
  );
}
