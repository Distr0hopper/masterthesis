export interface FormatPairDto {
  /** the output port's format */
  actualFormat: string;
  /** the input port's format */
  expectedFormat: string;
  ontologyUrl: string;
}

export interface FormatPairResultDto extends FormatPairDto {
  /** null when the pair couldn't be checked - treated as unverified */
  compatible: boolean | null;
}

export interface CompatibilityResponseDto {
  results: FormatPairResultDto[];
}
