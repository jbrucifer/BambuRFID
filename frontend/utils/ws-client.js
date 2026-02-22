/**
 * WebSocket client for communicating with the NFC bridge backend.
 */
class WSClient {
    constructor() {
        this.ws = null;
        this.connected = false;
        this.onStatusChange = null;
        this.reconnectTimer = null;
        this.reconnectDelay = 3000;
    }

    connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/ws/nfc-ui`;

        try {
            this.ws = new WebSocket(url);

            this.ws.onopen = () => {
                this.connected = true;
                if (this.onStatusChange) this.onStatusChange(true);
                console.log('WebSocket connected to backend');
            };

            this.ws.onclose = () => {
                this.connected = false;
                if (this.onStatusChange) this.onStatusChange(false);
                this.scheduleReconnect();
            };

            this.ws.onerror = (err) => {
                console.error('WebSocket error:', err);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.error('Invalid WS message:', e);
                }
            };
        } catch (e) {
            console.error('WebSocket connection failed:', e);
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        if (this.reconnectTimer) return;
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
        }, this.reconnectDelay);
    }

    handleMessage(data) {
        // Handle real-time updates from backend
        if (data.type === 'bridge_status') {
            updateBridgeStatus(data.connected);
        } else if (data.type === 'tag_detected') {
            showToast(`Tag detected: ${data.uid}`, 'info');
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    disconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

const wsClient = new WSClient();
