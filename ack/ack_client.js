"""ACK Client — JavaScript module for sending acknowledgments to the ACK server.

Usage:
    import { sendAck } from './ack_client.js';

    sendAck('http://localhost:8888', 'msg-123', 'received', 'hello world')
        .then(success => console.log('ACK sent:', success));
*/

/**
 * Send an ACK to the server with retry logic.
 *
 * @param {string} serverUrl - Base URL of the ACK server (e.g. 'http://localhost:8888')
 * @param {string} messageId - Unique message identifier
 * @param {string} status - 'received' or 'error'
 * @param {string} decodedMessage - The decoded message content
 * @param {number} [maxRetries=3] - Maximum number of retry attempts
 * @param {number} [retryInterval=1000] - Interval between retries in ms
 * @param {number} [timeout=5000] - Request timeout in ms
 * @returns {Promise<boolean>} True if the ACK was accepted, false otherwise
 */
async function sendAck(
    serverUrl,
    messageId,
    status,
    decodedMessage,
    maxRetries = 3,
    retryInterval = 1000,
    timeout = 5000,
) {
    const payload = {
        message_id: messageId,
        status: status,
        timestamp: new Date().toISOString(),
        decoded_message: decodedMessage || "",
    };

    const endpoint = serverUrl.replace(/\/$/, "") + "/ack";

    let lastError = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeout);

            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (response.ok) {
                const data = await response.json();
                if (data.ack === true) {
                    return true;
                }
            }

            lastError = new Error(`Server responded ${response.status}`);
        } catch (err) {
            lastError = err;
        }

        if (attempt < maxRetries) {
            await new Promise((resolve) => setTimeout(resolve, retryInterval));
        }
    }

    console.error(`ACK failed after ${maxRetries + 1} attempts:`, lastError);
    return false;
}

export { sendAck };
