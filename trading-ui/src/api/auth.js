import client from "./client";

export const authAPI = {
    login: async (email, password) => {
        const response = await client.post("/auth/login", { email, password });
        return response.data;
    },

    register: async (email, password) => {
        const response = await client.post("/auth/register", { email, password });
        return response.data;
    },

    getCurrentUser: async () => {
        const response = await client.get("/auth/me");
        return response.data;
    },

    sendOtp: async (phone) => {
        const response = await client.post("/auth/send-otp", { phone });
        return response.data;
    },

    verifyOtp: async (phone, otp) => {
        const response = await client.post("/auth/verify-otp", { phone, otp });
        return response.data;
    }
};
