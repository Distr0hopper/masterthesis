import { ApiProperty } from '@nestjs/swagger';
import { IsOptional, IsString } from 'class-validator';

export class UpdateComponentDto {
  @ApiProperty({ nullable: true, required: false })
  @IsOptional()
  @IsString()
  description: string | null;
}