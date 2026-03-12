import axios from "axios";
import { API_BASE } from "../lib/api";

const client = axios.create({
    baseURL: API_BASE,
    headers: {
        "Content-Type": "application/json",
    },
});



export default client;
