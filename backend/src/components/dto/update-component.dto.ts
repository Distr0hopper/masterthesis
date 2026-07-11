import { ApiProperty } from '@nestjs/swagger';
import { IsIn, IsOptional, IsString } from 'class-validator';
import { VALID_DOMAINS } from '../enums';

export class UpdateComponentDto {
  @ApiProperty({ nullable: true, required: false })
  @IsOptional()
  @IsString()
  description?: string | null;

  @ApiProperty({ enum: VALID_DOMAINS, required: false })
  @IsOptional()
  @IsIn(VALID_DOMAINS)
  domain?: string;
}