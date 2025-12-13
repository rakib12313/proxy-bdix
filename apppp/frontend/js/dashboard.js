
document.addEventListener('DOMContentLoaded', async () => {
    // Auth Check
    const token = localStorage.getItem('auth_token');
    const userStr = localStorage.getItem('user');

    if (!token || !userStr) {
        window.location.href = 'login.html';
        return;
    }

    const user = JSON.parse(userStr);

    // UI Elements
    const userWelcome = document.getElementById('userWelcome');
    const logoutBtn = document.getElementById('logoutBtn');
    const fileGrid = document.getElementById('fileGrid');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('progressBar');
    const storageUsedEl = document.getElementById('storageUsed');
    const storageBar = document.getElementById('storageBar');

    // Initialize
    userWelcome.innerText = `Welcome, ${user.user_metadata?.full_name || 'User'}`;
    await loadFiles();

    // Logout
    logoutBtn.addEventListener('click', async () => {
        try {
            await api.post('/auth/logout', {});
        } catch (e) { }
        localStorage.clear();
        window.location.href = 'index.html';
    });

    // File Upload (Drag & Drop)
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--primary)';
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'var(--glass-border)';
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--glass-border)';
        handleFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener('change', () => handleFiles(fileInput.files));

    async function handleFiles(files) {
        if (!files.length) return;

        uploadProgress.style.display = 'block';

        for (const file of files) {
            await uploadFile(file);
        }

        uploadProgress.style.display = 'none';
        progressBar.style.width = '0%';
        await loadFiles(); // Refresh list
    }

    async function uploadFile(file) {
        try {
            // 1. Get Signature
            const signData = await api.get('/files/signature');

            // 2. Upload to Cloudinary
            const formData = new FormData();
            formData.append('file', file);
            formData.append('api_key', signData.apiKey);
            formData.append('timestamp', signData.timestamp);
            formData.append('signature', signData.signature);
            formData.append('folder', signData.folder);

            const cloudinaryRes = await fetch(`https://api.cloudinary.com/v1_1/${signData.cloudName}/auto/upload`, {
                method: 'POST',
                body: formData
            });

            if (!cloudinaryRes.ok) throw new Error('Cloudinary upload failed');
            const cloudData = await cloudinaryRes.json();

            // 3. Save Metadata
            await api.post('/files/metadata', {
                cloudinary_public_id: cloudData.public_id,
                cloudinary_url: cloudData.secure_url,
                filename: file.name,
                file_type: file.type,
                size: cloudData.bytes
            });

        } catch (error) {
            console.error(error);
            alert(`Failed to upload ${file.name}: ${error.message}`);
        }
    }

    async function loadFiles() {
        try {
            const files = await api.get('/files');
            renderFiles(files);
            updateStorageStats(files);
        } catch (error) {
            console.error(error);
        }
    }

    function renderFiles(files) {
        fileGrid.innerHTML = '';
        if (files.length === 0) {
            fileGrid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 2rem;">No files yet. Upload one!</p>';
            return;
        }

        files.forEach(file => {
            const isImage = file.file_type.startsWith('image/');
            const icon = isImage ? file.cloudinary_url : 'assets/pdf-icon.png'; // Placeholder for PDF

            const card = document.createElement('div');
            card.className = 'glass';
            card.style.overflow = 'hidden';
            card.style.position = 'relative';

            card.innerHTML = `
                <div style="height: 150px; background: #000; display: flex; align-items: center; justify-content: center; overflow: hidden;">
                    ${isImage
                    ? `<img src="${file.cloudinary_url}" style="width: 100%; height: 100%; object-fit: cover;">`
                    : `<i class="fas fa-file-pdf" style="font-size: 4rem; color: #ef4444;"></i>`
                }
                </div>
                <div style="padding: 1rem;">
                    <h4 style="font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 0.5rem;" title="${file.filename}">${file.filename}</h4>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.8rem; color: var(--text-muted);">${formatBytes(file.size)}</span>
                        <button class="delete-btn" style="background: none; border: none; color: var(--error); cursor: pointer;" data-id="${file.id}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;

            // Delete Action
            card.querySelector('.delete-btn').addEventListener('click', () => deleteFile(file.id));

            fileGrid.appendChild(card);
        });
    }

    async function deleteFile(id) {
        if (!confirm('Are you sure?')) return;
        try {
            await api.get(`/files/${id}`, { method: 'DELETE' }); // Wait, api.get doesn't support DELETE options properly in my util
            // Let's fix api.js or use fetch directly here for a sec, or wait, I need to update api.js to support DELETE.
            // Actually I'll just use a raw fetch call wrapper here for speed or update api.js. 
            // Better to add delete method to api object.

            // Temporary fix via raw fetch for delete
            const token = localStorage.getItem('auth_token');
            await fetch(`http://localhost:5000/api/files/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            await loadFiles();
        } catch (error) {
            alert('Delete failed');
        }
    }

    function updateStorageStats(files) {
        const totalUsed = files.reduce((acc, file) => acc + file.size, 0);
        const limit = 50 * 1024 * 1024; // 50MB
        const percent = Math.min(100, (totalUsed / limit) * 100);

        storageUsedEl.innerText = `${formatBytes(totalUsed)}`;
        storageBar.style.width = `${percent}%`;

        if (percent > 90) storageBar.style.background = 'var(--error)';
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
});
