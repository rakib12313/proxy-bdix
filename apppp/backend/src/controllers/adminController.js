
const supabase = require('../config/supabase');

// 1. List All Users
const listUsers = async (req, res) => {
    try {
        const { data, error } = await supabase
            .from('profiles')
            .select('*')
            .order('created_at', { ascending: false });

        if (error) throw error;
        res.json(data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};

// 2. Suspend/Activate User
const toggleUserStatus = async (req, res) => {
    try {
        const { id } = req.params;
        const { is_suspended } = req.body; // Boolean

        const { data, error } = await supabase
            .from('profiles')
            .update({ is_suspended })
            .eq('id', id)
            .select()
            .single();

        if (error) throw error;
        res.json({ message: `User ${is_suspended ? 'suspended' : 'activated'}`, user: data });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};

// 3. System Analytics
const getSystemStats = async (req, res) => {
    try {
        // Parallel fetch
        const [usersRes, filesRes] = await Promise.all([
            supabase.from('profiles').select('id', { count: 'exact' }),
            supabase.from('files').select('size', { count: 'exact' })
        ]);

        // Calculate total storage (naive approach, better to do SQL sum if possible or store aggregate)
        // For now, since we don't have a fast sum API exposed easily without RPC, let's just count.
        // Actually, let's try to get a sum if we can, or just return counts for now.

        // Quick Fix: Create an RPC for this, but for now just mock the sum or fetch all (bad for perf).
        // Better: Just return counts.

        res.json({
            totalUsers: usersRes.count,
            totalFiles: filesRes.count,
            // totalStorage: ... (implementation depends on DB size)
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};

module.exports = {
    listUsers,
    toggleUserStatus,
    getSystemStats
};
