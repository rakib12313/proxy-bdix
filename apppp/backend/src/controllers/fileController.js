
const cloudinary = require('../config/cloudinary');
const supabase = require('../config/supabase');

// 1. Get Cloudinary Signature for Upload
// Checks quota first.
const getUploadSignature = async (req, res) => {
    try {
        const user = req.user;

        // Check Quota
        const { data: profile, error: profileError } = await supabase
            .from('profiles')
            .select('storage_used, storage_limit')
            .eq('id', user.id)
            .single();

        if (profileError) throw profileError;

        if (profile.storage_used >= profile.storage_limit) {
            return res.status(403).json({ error: 'Storage quota exceeded' });
        }

        const timestamp = Math.round((new Date()).getTime() / 1000);
        const folder = `users/${user.id}`;

        const signature = cloudinary.utils.api_sign_request({
            timestamp: timestamp,
            folder: folder,
        }, process.env.CLOUDINARY_API_SECRET);

        res.json({
            signature,
            timestamp,
            cloudName: process.env.CLOUDINARY_CLOUD_NAME,
            apiKey: process.env.CLOUDINARY_API_KEY,
            folder
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};

// 2. Save File Metadata (Called after successful Cloudinary upload)
const saveFileMetadata = async (req, res) => {
    try {
        const user = req.user;
        const {
            cloudinary_public_id,
            cloudinary_url,
            filename,
            file_type,
            size
        } = req.body;

        // 1. Insert File
        const { data: file, error: fileError } = await supabase
            .from('files')
            .insert({
                user_id: user.id,
                cloudinary_public_id,
                cloudinary_url,
                filename,
                file_type,
                size
            })
            .select()
            .single();

        if (fileError) throw fileError;

        // 2. Update User Storage Used (Atomic increment ideally, but simplified here)
        // Supabase doesn't support easy `storage_used + size` inside a JS client update easily without RPC
        // So we fetch, add, update, OR use an RPC. For now, let's just use raw SQL via RPC in production, 
        // but here we might just do a simple update for speed if RPC isn't set up.
        // BETTER: Recalculate or just add.

        const { data: profile } = await supabase.from('profiles').select('storage_used').eq('id', user.id).single();
        const newStorage = (parseInt(profile.storage_used) || 0) + size;

        await supabase
            .from('profiles')
            .update({ storage_used: newStorage })
            .eq('id', user.id);

        res.status(201).json({ message: 'File saved', file });
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: error.message });
    }
};

// 3. List User Files
const listFiles = async (req, res) => {
    try {
        const user = req.user;
        const { data, error } = await supabase
            .from('files')
            .select('*')
            .eq('user_id', user.id)
            .order('created_at', { ascending: false });

        if (error) throw error;
        res.json(data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};

// 4. Delete File
const deleteFile = async (req, res) => {
    try {
        const user = req.user;
        const { id } = req.params;

        // Get file first to check ownership and get cloudinary ID
        const { data: file, error: fetchError } = await supabase
            .from('files')
            .select('*')
            .eq('id', id)
            .eq('user_id', user.id)
            .single();

        if (fetchError || !file) return res.status(404).json({ error: 'File not found' });

        // Delete from Cloudinary
        await cloudinary.uploader.destroy(file.cloudinary_public_id);

        // Delete from DB
        const { error: deleteError } = await supabase
            .from('files')
            .delete()
            .eq('id', id);

        if (deleteError) throw deleteError;

        // Update Quota
        const { data: profile } = await supabase.from('profiles').select('storage_used').eq('id', user.id).single();
        const newStorage = Math.max(0, (parseInt(profile.storage_used) || 0) - file.size);

        await supabase.from('profiles').update({ storage_used: newStorage }).eq('id', user.id);

        res.json({ message: 'File deleted' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};

module.exports = {
    getUploadSignature,
    saveFileMetadata,
    listFiles,
    deleteFile
};
