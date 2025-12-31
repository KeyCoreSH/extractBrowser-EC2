module.exports = {
    apps: [{
        name: "extractbrowser",
        script: "app.py",
        interpreter: "venv/bin/python",
        instances: 1,
        autorestart: true,
        watch: false,
        max_memory_restart: '1G',
        env: {
            NODE_ENV: "production",
            PORT: 2345
        }
    }]
};
