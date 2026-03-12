import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = "https://sneak-3jg1.onrender.com";

async function proxyRequest(req: NextRequest) {
    const url = new URL(req.url);
    // Reconstruct the path: /api/v1/analyze -> /api/v1/analyze
    const targetUrl = `${BACKEND_URL}${url.pathname}${url.search}`;

    const headers = new Headers();
    headers.set("Content-Type", req.headers.get("Content-Type") || "application/json");

    const fetchOptions: RequestInit = {
        method: req.method,
        headers,
    };

    // Forward body for non-GET/HEAD requests
    if (req.method !== "GET" && req.method !== "HEAD") {
        fetchOptions.body = await req.text();
    }

    try {
        const response = await fetch(targetUrl, fetchOptions);
        const data = await response.text();

        return new NextResponse(data, {
            status: response.status,
            statusText: response.statusText,
            headers: {
                "Content-Type": response.headers.get("Content-Type") || "application/json",
            },
        });
    } catch (error) {
        console.error("Proxy error:", error);
        return NextResponse.json(
            { error: "Backend service unavailable" },
            { status: 502 }
        );
    }
}

export async function GET(req: NextRequest) {
    return proxyRequest(req);
}

export async function POST(req: NextRequest) {
    return proxyRequest(req);
}

export async function PATCH(req: NextRequest) {
    return proxyRequest(req);
}

export async function PUT(req: NextRequest) {
    return proxyRequest(req);
}

export async function DELETE(req: NextRequest) {
    return proxyRequest(req);
}

export async function OPTIONS(req: NextRequest) {
    return proxyRequest(req);
}
