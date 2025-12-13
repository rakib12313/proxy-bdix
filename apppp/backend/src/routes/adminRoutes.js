
const express = require('express');
const router = express.Router();
const { listUsers, toggleUserStatus, getSystemStats } = require('../controllers/adminController');
const authenticate = require('../middleware/auth');

// Middleware to check if user is admin
const requireAdmin = (req, res, next) => {
    if (req.user && req.user.role === 'admin') {
        next();
    } else {
        // Check DB profile if role not in JWT metadata yet
        // For now assuming role is synced or fetched. request.user usually comes from auth stub.
        // Let's rely on our auth middleware which fetches user.
        // Wait, the supabase.auth.getUser() returns auth.users data. We need public.profiles role.
        // We should fetching profile in auth middleware or here.
        return res.status(403).json({ error: 'Access denied: Admins only' });
    }
};

// Enhance auth middleware to fetch profile role? 
// Or just do it here.
const adminCheck = async (req, res, next) => {
    // TODO: proper role check via DB or claim
    // For MVP, user needs to manually add role check logic here 
    // IF we trust the metadata or fetch profile.

    const supabase = require('../config/supabase');
    const { data: profile } = await supabase.from('profiles').select('role').eq('id', req.user.id).single();

    if (profile && profile.role === 'admin') {
        next();
    } else {
        res.status(403).json({ error: 'Access denied. Admin role required.' });
    }
};

router.use(authenticate);
router.use(adminCheck);

router.get('/users', listUsers);
router.put('/users/:id/status', toggleUserStatus);
router.get('/stats', getSystemStats);

module.exports = router;
