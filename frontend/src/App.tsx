import { Route, Routes } from 'react-router-dom';
import Shell from './components/Shell';
import GamePage from './pages/GamePage';
import NotFoundPage from './pages/NotFoundPage';
import ReviewsPage from './pages/ReviewsPage';
import SearchPage from './pages/SearchPage';

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<SearchPage />} />
        <Route path="games/:id" element={<GamePage />} />
        <Route path="games/:id/reviews" element={<ReviewsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
