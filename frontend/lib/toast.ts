import { toast } from "sonner";
import { ApiError } from "@/lib/api";

export function errorText(error: unknown): { title: string; description?: string } {
  if (error instanceof ApiError) {
    const fields = error.fieldErrors.map((e) => `${e.field}: ${e.message}`).join("; ");
    const description = [error.description, fields].filter(Boolean).join(" — ");
    return { title: error.message, description: description || undefined };
  }
  if (error instanceof Error) return { title: error.message };
  return { title: "Something went wrong" };
}

export function toastError(error: unknown): void {
  // 401s redirect to the login page; no need to shout about each failed poll.
  if (error instanceof ApiError && error.code === 401) return;
  const { title, description } = errorText(error);
  toast.error(title, { description });
}

export function toastSuccess(title: string, description?: string): void {
  toast.success(title, { description });
}
