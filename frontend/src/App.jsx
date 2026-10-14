import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { CardSkeleton } from "./components/LoadingSkeleton";
const Dashboard = lazy(() => import("./pages/Dashboard").then(module => ({ default: module.Dashboard })));
const Products = lazy(() => import("./pages/Products").then(module => ({ default: module.Products })));
const Dealers = lazy(() => import("./pages/Dealers").then(module => ({ default: module.Dealers })));
const Orders = lazy(() => import("./pages/Orders").then(module => ({ default: module.Orders })));
const Assistant = lazy(() => import("./pages/Assistant").then(module => ({ default: module.Assistant })));
const Forecasting = lazy(() => import("./pages/Forecasting").then(module => ({ default: module.Forecasting })));
export default function App() {
  return <BrowserRouter><Layout><Suspense fallback={<CardSkeleton />}><Routes>
    <Route path="/" element={<Dashboard />} />
    <Route path="/products" element={<Products />} />
    <Route path="/dealers" element={<Dealers />} />
    <Route path="/orders" element={<Orders />} />
    <Route path="/assistant" element={<Assistant />} />
    <Route path="/forecasting" element={<Forecasting />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></Suspense></Layout></BrowserRouter>;
}
