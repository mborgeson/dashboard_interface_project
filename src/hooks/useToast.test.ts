import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useToast } from "./useToast";
import { useNotificationStore } from "@/stores/notificationStore";

// Mock the notification store
vi.mock("@/stores/notificationStore", () => ({
  useNotificationStore: vi.fn(),
}));

describe("useToast", () => {
  const mockAddToast = vi.fn().mockReturnValue("toast-id-1");
  const mockRemoveToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (
      useNotificationStore as unknown as ReturnType<typeof vi.fn>
    ).mockReturnValue({
      addToast: mockAddToast,
      removeToast: mockRemoveToast,
    });
  });

  it("returns toast function", () => {
    const { result } = renderHook(() => useToast());

    expect(typeof result.current.toast).toBe("function");
  });

  it("returns success, error, warning, info helpers", () => {
    const { result } = renderHook(() => useToast());

    expect(typeof result.current.success).toBe("function");
    expect(typeof result.current.error).toBe("function");
    expect(typeof result.current.warning).toBe("function");
    expect(typeof result.current.info).toBe("function");
  });

  it("returns dismiss function", () => {
    const { result } = renderHook(() => useToast());

    expect(typeof result.current.dismiss).toBe("function");
  });

  describe("toast()", () => {
    it("calls addToast with options", () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.toast({
          type: "success",
          title: "Test Toast",
          description: "Test description",
        });
      });

      expect(mockAddToast).toHaveBeenCalledWith({
        type: "success",
        title: "Test Toast",
        description: "Test description",
      });
    });

    it("returns toast id", () => {
      const { result } = renderHook(() => useToast());

      let toastId: string | undefined;
      act(() => {
        toastId = result.current.toast({
          type: "info",
          title: "Test",
        });
      });

      expect(toastId).toBe("toast-id-1");
    });
  });

  describe("success()", () => {
    it("calls addToast with success type", () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.success("Success!");
      });

      expect(mockAddToast).toHaveBeenCalledWith({
        type: "success",
        title: "Success!",
      });
    });

    it("passes additional options", () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.success("Success!", {
          description: "Extra info",
          duration: 3000,
        });
      });

      expect(mockAddToast).toHaveBeenCalledWith({
        type: "success",
        title: "Success!",
        description: "Extra info",
        duration: 3000,
      });
    });
  });

  describe("error()", () => {
    it("calls addToast with error type", () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.error("Error occurred");
      });

      expect(mockAddToast).toHaveBeenCalledWith({
        type: "error",
        title: "Error occurred",
      });
    });
  });

  describe("warning()", () => {
    it("calls addToast with warning type", () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.warning("Warning message");
      });

      expect(mockAddToast).toHaveBeenCalledWith({
        type: "warning",
        title: "Warning message",
      });
    });
  });

  describe("info()", () => {
    it("calls addToast with info type", () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.info("Info message");
      });

      expect(mockAddToast).toHaveBeenCalledWith({
        type: "info",
        title: "Info message",
      });
    });
  });

  describe("dismiss()", () => {
    it("calls removeToast with id", () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.dismiss("toast-to-remove");
      });

      expect(mockRemoveToast).toHaveBeenCalledWith("toast-to-remove");
    });
  });
});
