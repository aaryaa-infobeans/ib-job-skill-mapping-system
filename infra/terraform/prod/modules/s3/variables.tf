variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "buckets" {
  description = "Map of S3 buckets to create"
  type = map(object({
    versioning_enabled = bool
    lifecycle_rules = list(object({
      id                                  = string
      enabled                             = bool
      expiration_days                     = optional(number)
      transition_days                     = optional(number)
      storage_class                       = optional(string)
      noncurrent_version_expiration_days  = optional(number)
    }))
  }))
  default = {}
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
