import { createFileRoute } from "@tanstack/react-router";
import { Purchase } from "@/features/Purchase";

export const Route = createFileRoute("/")({
	component: Purchase,
});
