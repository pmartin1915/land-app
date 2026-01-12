import toast, { Toaster as HotToaster, ToastOptions } from 'react-hot-toast'
import { CheckCircle, XCircle, AlertCircle, Loader2, Info } from 'lucide-react'

// Re-export the toast function with custom defaults
// eslint-disable-next-line react-refresh/only-export-components
export { toast }

// Toast wrapper with theme support
export function Toaster() {
  return (
    <HotToaster
      position="bottom-right"
      gutter={8}
      containerClassName=""
      toastOptions={{
        // Default options for all toasts
        duration: 4000,
        className: '',
        style: {
          background: 'var(--color-card)',
          color: 'var(--color-text-primary)',
          border: '1px solid var(--color-neutral-1)',
          borderRadius: '0.5rem',
          padding: '12px 16px',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
        // Custom styles per toast type
        success: {
          iconTheme: {
            primary: 'var(--color-success)',
            secondary: 'white',
          },
        },
        error: {
          iconTheme: {
            primary: 'var(--color-danger)',
            secondary: 'white',
          },
          duration: 5000,
        },
      }}
    />
  )
}

// Custom toast variants with icons
interface CustomToastOptions extends Omit<ToastOptions, 'icon'> {
  description?: string
}

// eslint-disable-next-line react-refresh/only-export-components
export const showToast = {
  success: (message: string, options?: CustomToastOptions) => {
    const { description, ...toastOptions } = options || {}
    return toast.success(
      <ToastContent message={message} description={description} />,
      {
        icon: <CheckCircle className="w-5 h-5 text-success" />,
        ...toastOptions,
      }
    )
  },

  error: (message: string, options?: CustomToastOptions) => {
    const { description, ...toastOptions } = options || {}
    return toast.error(
      <ToastContent message={message} description={description} />,
      {
        icon: <XCircle className="w-5 h-5 text-danger" />,
        ...toastOptions,
      }
    )
  },

  warning: (message: string, options?: CustomToastOptions) => {
    const { description, ...toastOptions } = options || {}
    return toast(
      <ToastContent message={message} description={description} />,
      {
        icon: <AlertCircle className="w-5 h-5 text-warning" />,
        ...toastOptions,
      }
    )
  },

  info: (message: string, options?: CustomToastOptions) => {
    const { description, ...toastOptions } = options || {}
    return toast(
      <ToastContent message={message} description={description} />,
      {
        icon: <Info className="w-5 h-5 text-accent-primary" />,
        ...toastOptions,
      }
    )
  },

  loading: (message: string, options?: CustomToastOptions) => {
    const { description, ...toastOptions } = options || {}
    return toast.loading(
      <ToastContent message={message} description={description} />,
      {
        icon: <Loader2 className="w-5 h-5 text-accent-primary animate-spin" />,
        ...toastOptions,
      }
    )
  },

  // Promise-based toast for async operations
  promise: <T,>(
    promise: Promise<T>,
    messages: {
      loading: string
      success: string | ((data: T) => string)
      error: string | ((err: Error) => string)
    },
    options?: ToastOptions
  ) => {
    return toast.promise(
      promise,
      {
        loading: <ToastContent message={messages.loading} />,
        success: (data) => (
          <ToastContent
            message={typeof messages.success === 'function' ? messages.success(data) : messages.success}
          />
        ),
        error: (err) => (
          <ToastContent
            message={typeof messages.error === 'function' ? messages.error(err) : messages.error}
          />
        ),
      },
      options
    )
  },

  // Dismiss a specific toast or all toasts
  dismiss: (toastId?: string) => {
    if (toastId) {
      toast.dismiss(toastId)
    } else {
      toast.dismiss()
    }
  },
}

// Toast content component for consistent formatting
interface ToastContentProps {
  message: string
  description?: string
}

function ToastContent({ message, description }: ToastContentProps) {
  return (
    <div className="flex flex-col">
      <span className="font-medium text-sm">{message}</span>
      {description && (
        <span className="text-xs text-text-muted mt-0.5">{description}</span>
      )}
    </div>
  )
}

// Action toast with button
interface ActionToastOptions extends CustomToastOptions {
  actionLabel: string
  onAction: () => void
}

// eslint-disable-next-line react-refresh/only-export-components
export function showActionToast(message: string, options: ActionToastOptions) {
  const { description, actionLabel, onAction, ...toastOptions } = options

  return toast(
    (t) => (
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <ToastContent message={message} description={description} />
        </div>
        <button
          onClick={() => {
            onAction()
            toast.dismiss(t.id)
          }}
          className="px-3 py-1 text-xs font-medium bg-accent-primary text-white rounded hover:bg-opacity-90 transition-colors"
        >
          {actionLabel}
        </button>
      </div>
    ),
    {
      duration: 6000,
      ...toastOptions,
    }
  )
}

// Undo toast for destructive actions
interface UndoToastOptions extends Omit<CustomToastOptions, 'duration'> {
  onUndo: () => void
  duration?: number
}

// eslint-disable-next-line react-refresh/only-export-components
export function showUndoToast(message: string, options: UndoToastOptions) {
  const { onUndo, duration = 5000, ...restOptions } = options

  return showActionToast(message, {
    actionLabel: 'Undo',
    onAction: onUndo,
    duration,
    ...restOptions,
  })
}
