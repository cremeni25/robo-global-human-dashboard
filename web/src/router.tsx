import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import LayoutGlobal from "./layout/LayoutGlobal";

import Home from "./pages/Home";
import Nichos from "./pages/Nichos";
import Dores from "./pages/Dores";
import Sobre from "./pages/Sobre";
import Ofertas from "./pages/Ofertas";

// O painel de operação só é baixado por quem acessa /admin.
const Admin = lazy(() => import("./pages/Admin"));

export default function Router() {
  return (
    <Routes>
      <Route element={<LayoutGlobal />}>
        <Route path="/" element={<Home />} />
        <Route path="/nichos" element={<Nichos />} />
        <Route path="/dores" element={<Dores />} />
        <Route path="/sobre" element={<Sobre />} />
        <Route path="/ofertas" element={<Ofertas />} />
        <Route path="/admin" element={<Suspense fallback={<p className="adm">…</p>}><Admin /></Suspense>} />
      </Route>
    </Routes>
  );
}
